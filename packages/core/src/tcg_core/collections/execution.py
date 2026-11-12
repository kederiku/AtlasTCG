"""Execute the next queued request using a framework-independent collector port."""

from tcg_core.collections.models import CollectionRequest
from tcg_core.collections.ports import Collector, JobQueue


class ExecuteCollection:
    def __init__(self, store: JobQueue) -> None:
        self.store = store

    def execute_next(self, collector: Collector) -> bool:
        job = self.store.claim()
        if job is None:
            return False
        try:
            result = collector.run(job["id"], CollectionRequest(**job["parameters"]))
        except Exception as error:
            self.store.finish(job["id"], "failed", {}, str(error))
        else:
            self.store.finish(job["id"], result.status, result.stats, result.error)
        return True
