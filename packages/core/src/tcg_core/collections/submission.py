"""Persist a validated request before any collection is executed."""

from tcg_core.collections.models import CollectionRequest, JobRecord
from tcg_core.collections.ports import JobSubmitter


class RequestCollection:
    def __init__(self, store: JobSubmitter) -> None:
        self.store = store

    def request(self, request: CollectionRequest) -> JobRecord:
        return self.store.enqueue(request.model_dump())
