"""Persist a validated request before any collection is executed."""

from tcg_core.collections.models import JobRecord, JobRequest
from tcg_core.collections.ports import JobSubmitter


class RequestCollection:
    def __init__(self, store: JobSubmitter) -> None:
        self.store = store

    def request(self, request: JobRequest) -> JobRecord:
        return self.store.enqueue(request.model_dump())
