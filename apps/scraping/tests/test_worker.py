"""Exercise the worker lock, signals and persistent queue with a local child."""

import os
import signal
import subprocess
import sys
import time

import pytest
from tcg_core.collections.models import CollectionRequest
from tcg_persistence.catalog import Repository
from tcg_persistence.jobs import JobRepository
from tcg_persistence.schema import metadata


def test_exclusive_worker_shutdown_interrupts_child_and_preserves_next_request(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    repository = Repository(database_url)
    metadata.create_all(repository.engine)
    store = JobRepository(repository.engine)
    first = store.enqueue(CollectionRequest(languages=["fr"]).model_dump())
    second = store.enqueue(CollectionRequest(languages=["en"]).model_dump())
    queued_observation = store.get(second["id"])
    pid_file = tmp_path / "child.pid"
    child_script = tmp_path / "local_collection.py"
    child_script.write_text(f"""
import os
import time
from pathlib import Path
Path({str(pid_file)!r}).write_text(str(os.getpid()))
time.sleep(60)
""")
    worker_script = tmp_path / "local_worker.py"
    worker_script.write_text(f"""
import sys
from tcg_scraping import worker
from tcg_scraping.runner import ScrapyCollector
class LocalCollector(ScrapyCollector):
    def command(self, identifier, request):
        return [sys.executable, {str(child_script)!r}]
# Substitute only the external collection command; keep the real worker and runner.
worker.ScrapyCollector = LocalCollector
worker.main()
""")
    environment = os.environ | {
        "TCG_DATABASE_URL": database_url,
        "TCG_JOBS_DIR": str(tmp_path / "jobs"),
        "TCG_IMAGES_DIR": str(tmp_path / "images"),
    }
    worker = subprocess.Popen(
        [sys.executable, str(worker_script)],
        cwd=tmp_path,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    child_pid = None
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if pid_file.exists() and pid_file.stat().st_size:
                child_pid = int(pid_file.read_text())
                break
            assert worker.poll() is None, worker.communicate()
            time.sleep(0.01)
        assert child_pid is not None, "The worker did not start its local collection"
        running_observation = store.get(first["id"])
        assert running_observation["status"] == "running"
        assert running_observation["started_at"] is not None

        duplicate = subprocess.run(
            [sys.executable, "-m", "tcg_scraping.worker"],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert duplicate.returncode != 0
        assert "already uses this jobs directory" in duplicate.stderr
        assert worker.poll() is None
        os.kill(child_pid, 0)
        assert store.get(first["id"]) == running_observation
        assert store.get(second["id"]) == queued_observation

        worker.send_signal(signal.SIGTERM)
        stdout, stderr = worker.communicate(timeout=15)
        assert worker.returncode == 0, stdout + stderr
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
        interrupted = store.get(first["id"])
        assert interrupted["status"] == "interrupted"
        assert interrupted["started_at"] == running_observation["started_at"]
        assert interrupted["finished_at"] >= interrupted["started_at"]
        assert interrupted["error"]
        assert store.get(second["id"]) == queued_observation
    finally:
        if worker.poll() is None:
            worker.terminate()
            try:
                worker.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.communicate()
        if child_pid is not None:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        repository.close()
