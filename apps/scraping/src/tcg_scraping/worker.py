"""Single local worker. Run independently from the HTTP server."""

import os
import signal
import time
from pathlib import Path

from filelock import FileLock, Timeout
from tcg_core.collections.execution import ExecuteCollection
from tcg_persistence.catalog import Repository
from tcg_persistence.configuration import database_url as configured_database_url
from tcg_persistence.jobs import JobRepository

from tcg_scraping.runner import ScrapyCollector


def main():
    directory = Path(os.getenv("TCG_JOBS_DIR", "data/jobs/admin")).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    repository = Repository(configured_database_url())
    store = JobRepository(repository.engine)
    service = ExecuteCollection(store)
    collector = ScrapyCollector(directory)

    def stop(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        with FileLock(directory / "worker.lock", timeout=0):
            store.recover()
            print("TCG worker ready (one collection at a time).", flush=True)
            try:
                while True:
                    if not service.execute_next(collector):
                        time.sleep(1)
            except KeyboardInterrupt:
                store.recover()
    except Timeout:
        raise SystemExit("A worker already uses this jobs directory") from None
    finally:
        repository.close()


if __name__ == "__main__":
    main()
