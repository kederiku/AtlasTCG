"""Collection requests and outcomes; no HTTP, SQL or subprocess dependencies."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from tcg_core.collections.connectors import CONNECTORS


class CollectionParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spider: Literal["tcgdex"] = "tcgdex"
    languages: list[str] = Field(
        default_factory=lambda: ["fr", "en"],
        min_length=1,
        max_length=len(CONNECTORS[0]["languages"]),
    )
    force: bool = False

    @field_validator("languages")
    @classmethod
    def known_languages(cls, values: list[str]) -> list[str]:
        if any(value not in CONNECTORS[0]["languages"] for value in values):
            raise ValueError("Unsupported language")
        return list(dict.fromkeys(values))


class CollectionRequest(CollectionParameters):
    card_ids: list[str] = Field(default_factory=list, max_length=100)
    limit: int = Field(default=10, ge=1, le=10000)

    @field_validator("card_ids")
    @classmethod
    def safe_ids(cls, values: list[str]) -> list[str]:
        if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value) for value in values):
            raise ValueError("Invalid card identifier")
        return list(dict.fromkeys(values))


class CollectionScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["block", "set"]
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class ScopedCollectionRequest(CollectionParameters):
    kind: Literal["collect_scope"]
    scope: CollectionScope


class ImageRepairRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["repair_images"]


JobRequest = CollectionRequest | ScopedCollectionRequest | ImageRepairRequest
job_request_adapter: TypeAdapter[JobRequest] = TypeAdapter(JobRequest)


JobStatus = Literal["queued", "running", "succeeded", "failed", "interrupted"]
CompletedStatus = Literal["succeeded", "failed"]


class JobRecord(TypedDict):
    id: str
    status: JobStatus
    parameters: dict[str, Any]
    stats: dict[str, Any]
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True)
class CollectionResult:
    status: CompletedStatus
    stats: dict[str, Any]
    error: str | None = None
