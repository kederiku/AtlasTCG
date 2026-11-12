"""Read collection history and logs without depending on SQL or files."""

from tcg_core.collections.models import JobRecord
from tcg_core.collections.ports import JobLogReader, JobReader


class CollectionQueries:
    def __init__(self, store: JobReader, logs: JobLogReader) -> None:
        self.store = store
        self.log_reader = logs

    def list(self) -> list[JobRecord]:
        return self.store.list()

    def get(self, identifier: str) -> JobRecord | None:
        return self.store.get(identifier)

    def logs(self, identifier: str) -> str | None:
        if self.store.get(identifier) is None:
            return None
        return self.log_reader.read(identifier)
