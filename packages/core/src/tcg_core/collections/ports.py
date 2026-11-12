"""Narrow contracts for collection requests, execution and consultation."""

from typing import Any, Protocol

from tcg_core.collections.models import CollectionRequest, CollectionResult, JobRecord, JobStatus


class JobSubmitter(Protocol):
    def enqueue(self, parameters: dict[str, Any]) -> JobRecord: ...


class JobQueue(Protocol):
    def claim(self) -> JobRecord | None: ...
    def finish(
        self, identifier: str, status: JobStatus, stats: dict[str, Any], error: str | None = None
    ) -> None: ...


class JobReader(Protocol):
    def list(self) -> list[JobRecord]: ...
    def get(self, identifier: str) -> JobRecord | None: ...


class JobLogReader(Protocol):
    def read(self, identifier: str) -> str: ...


class Collector(Protocol):
    def run(self, identifier: str, request: CollectionRequest) -> CollectionResult: ...
