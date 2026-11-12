"""Observe process results and cleanup using local Python children only."""

import os
import signal
import subprocess
import sys
import time

import pytest
from tcg_core.collections.models import CollectionRequest
from tcg_scraping.runner import ScrapyCollector, collection_result


@pytest.mark.parametrize(
    ("code", "stats", "status"),
    [
        (0, {"finish_reason": "finished", "cards/skipped_existing": 2}, "succeeded"),
        (0, {"finish_reason": "finished", "item_dropped_count": 1}, "failed"),
        (0, {"finish_reason": "finished", "log_count/ERROR": 1}, "failed"),
        (0, {"finish_reason": "robotstxt_denied"}, "failed"),
        (0, {}, "failed"),
        (1, {"finish_reason": "finished"}, "failed"),
    ],
)
def test_scrapy_diagnostics_determine_result(code, stats, status):
    result = collection_result(code, stats)
    assert result.status == status
    assert result.stats == stats
    assert bool(result.error) == (status == "failed")


def test_timeout_terminates_the_collection_child(tmp_path):
    pid_file = tmp_path / "child.pid"

    class SlowCollector(ScrapyCollector):
        def command(self, identifier, request):
            return [
                sys.executable,
                "-c",
                (
                    "import os, time; from pathlib import Path; "
                    f"Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(30)"
                ),
            ]

    with pytest.raises(subprocess.TimeoutExpired):
        SlowCollector(tmp_path, timeout=1).run("one", CollectionRequest())
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)


def test_interruption_terminates_the_collection_child(tmp_path):
    pid_file = tmp_path / "child.pid"
    script = tmp_path / "runner.py"
    script.write_text(f"""
import sys
from tcg_core.collections.models import CollectionRequest
from tcg_scraping.runner import ScrapyCollector
class SlowCollector(ScrapyCollector):
    def command(self, identifier, request):
        return [sys.executable, '-c', {
        (
            "import os, time; from pathlib import Path; "
            f"Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(30)"
        )!r
    }]
SlowCollector({str(tmp_path)!r}).run('one', CollectionRequest())
""")
    process = subprocess.Popen([sys.executable, str(script)], stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 5
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert pid_file.exists()
        process.send_signal(signal.SIGINT)
        process.communicate(timeout=5)
        assert process.returncode != 0
        with pytest.raises(ProcessLookupError):
            os.kill(int(pid_file.read_text()), 0)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def test_scrapy_launcher_discovers_connectors_outside_repository(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "tcg_scraping.cli.scrape", "list"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["tcgdex"]
