import pytest
from sqlalchemy import create_engine
from tcg_core.collections.execution import ExecuteCollection
from tcg_core.collections.models import CollectionRequest, CollectionResult
from tcg_core.collections.submission import RequestCollection
from tcg_persistence.jobs import JobRepository
from tcg_persistence.schema import metadata
from tcg_scraping.runner import collection_result


@pytest.fixture
def store(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'jobs.db'}")
    metadata.create_all(engine)
    yield JobRepository(engine)
    engine.dispose()


@pytest.mark.parametrize(
    ("code", "stats", "expected"),
    [
        (0, {"finish_reason": "finished", "cards/skipped_existing": 2}, "succeeded"),
        (0, {"finish_reason": "robotstxt_denied"}, "failed"),
        (0, {"finish_reason": "finished", "log_count/ERROR": 1}, "failed"),
        (1, {}, "failed"),
    ],
)
def test_worker_records_actual_outcome_even_when_scrapy_exits_zero(store, code, stats, expected):
    class Collector:
        def run(self, identifier, request):
            return collection_result(code, stats)

    service = RequestCollection(store)
    job = service.request(CollectionRequest())
    assert ExecuteCollection(store).execute_next(Collector())
    result = store.get(job["id"])
    assert result["status"] == expected
    assert result["stats"] == stats
    assert not ExecuteCollection(store).execute_next(Collector())


def test_restarting_worker_marks_interrupted_jobs_and_preserves_queue(store):
    service = RequestCollection(store)
    running = service.request(CollectionRequest())
    queued = service.request(CollectionRequest())
    store.claim()
    store.recover()
    assert store.get(running["id"])["status"] == "interrupted"
    assert store.get(queued["id"])["status"] == "queued"


@pytest.mark.parametrize("error_type", [RuntimeError, TimeoutError])
def test_collector_exception_is_persisted_without_blocking_the_next_request(store, error_type):
    service = RequestCollection(store)
    failed = service.request(CollectionRequest(card_ids=["base1-4"]))
    following = service.request(CollectionRequest(card_ids=["base1-5"]))

    class Collector:
        def run(self, identifier, request):
            if request.card_ids == ["base1-4"]:
                raise error_type("Local collector unavailable")
            return CollectionResult(status="succeeded", stats={"cards/stored": 1})

    execution = ExecuteCollection(store)
    collector = Collector()
    assert execution.execute_next(collector)
    persisted = store.get(failed["id"])
    assert persisted["status"] == "failed"
    assert persisted["error"] == "Local collector unavailable"
    assert persisted["stats"] == {}
    assert persisted["parameters"]["card_ids"] == ["base1-4"]
    assert persisted["created_at"] <= persisted["started_at"] <= persisted["finished_at"]
    waiting = store.get(following["id"])
    assert waiting["status"] == "queued"
    assert waiting["started_at"] is None
    assert waiting["finished_at"] is None

    assert execution.execute_next(collector)
    completed = store.get(following["id"])
    assert completed["status"] == "succeeded"
    assert completed["error"] is None
    assert completed["stats"] == {"cards/stored": 1}
    assert completed["created_at"] <= completed["started_at"] <= completed["finished_at"]
    assert not execution.execute_next(collector)


def test_subprocess_command_cannot_take_arbitrary_shell_options(tmp_path):
    from tcg_scraping.runner import ScrapyCollector

    request = CollectionRequest(languages=["fr"], card_ids=["base1-4"], limit=2)
    command = ScrapyCollector(tmp_path).command("run", request)
    assert command[1:4] == ["-m", "scrapy", "crawl"]
    assert "card_ids=base1-4" in command
    assert "force=false" in command
