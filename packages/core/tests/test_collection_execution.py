"""The application consumes a collection result, not framework statistics."""

from tcg_core.collections.execution import ExecuteCollection
from tcg_core.collections.models import CollectionResult


def test_repair_request_reaches_the_collector_without_becoming_a_collection():
    class Queue:
        finished = None

        def claim(self):
            return {"id": "repair", "parameters": {"kind": "repair_images"}}

        def finish(self, identifier, status, stats, error=None):
            self.finished = (identifier, status, stats, error)

    class Collector:
        def run(self, identifier, request):
            assert request.model_dump() == {"kind": "repair_images"}
            return CollectionResult(status="succeeded", stats={"images/downloaded": 2})

    queue = Queue()
    assert ExecuteCollection(queue).execute_next(Collector())
    assert queue.finished == ("repair", "succeeded", {"images/downloaded": 2}, None)


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
