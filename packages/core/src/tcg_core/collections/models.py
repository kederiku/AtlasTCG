"""Collection requests and outcomes; no HTTP, SQL or subprocess dependencies."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tcg_core.collections.connectors import CONNECTORS


class CollectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spider: Literal["tcgdex"] = "tcgdex"
    languages: list[str] = Field(
        default_factory=lambda: ["fr", "en"],
        min_length=1,
        max_length=len(CONNECTORS[0]["languages"]),
    )
    card_ids: list[str] = Field(default_factory=list, max_length=100)
    limit: int = Field(default=10, ge=1, le=10000)
    force: bool = False

    @field_validator("languages")
    @classmethod
    def known_languages(cls, values: list[str]) -> list[str]:
        if any(value not in CONNECTORS[0]["languages"] for value in values):
            raise ValueError("Unsupported language")
        return list(dict.fromkeys(values))

    @field_validator("card_ids")
    @classmethod
    def safe_ids(cls, values: list[str]) -> list[str]:
        if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value) for value in values):
            raise ValueError("Invalid card identifier")
        return list(dict.fromkeys(values))


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
