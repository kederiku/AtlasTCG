"""The application consumes a collection result, not framework statistics."""

from tcg_core.collections.execution import ExecuteCollection
from tcg_core.collections.models import CollectionResult


def test_success_is_reported_by_collector_not_inferred_from_diagnostic_keys():
    class Queue:
        record = {"id": "one", "parameters": {}}
        finished = None

        def claim(self):
            record, self.record = self.record, None
            return record

        def finish(self, identifier, status, stats, error=None):
            self.finished = {"id": identifier, "status": status, "stats": stats, "error": error}

    class Collector:
        def run(self, identifier, request):
            return CollectionResult(status="succeeded", stats={"observations": 2}, error=None)

    queue = Queue()
    service = ExecuteCollection(queue)
    assert service.execute_next(Collector())
    assert queue.finished == {
        "id": "one",
        "status": "succeeded",
        "stats": {"observations": 2},
        "error": None,
    }
    assert not service.execute_next(Collector())
