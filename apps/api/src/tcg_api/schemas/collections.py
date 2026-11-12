"""Public collection contracts, independent of database column discovery."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_serializer
from tcg_core.collections.models import CollectionRequest, JobStatus


class ConnectorView(BaseModel):
    id: str
    name: str
    game: str
    languages: list[str]


class JobView(BaseModel):
    id: str
    status: JobStatus
    parameters: CollectionRequest
    stats: dict[str, Any]
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @field_serializer("created_at", "started_at", "finished_at", when_used="json")
    def serialize_date(self, value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None
