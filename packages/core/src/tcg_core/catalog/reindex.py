"""Reproject stored source observations without downloading cards or images."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import ValidationError

from tcg_core.catalog.models import CATALOG_VERSION, Card


class ObservationStore(Protocol):
    def observations(self, source: str) -> Iterable[dict[str, Any]]: ...
    def save(self, item: dict[str, Any], *, preserve_updated_at: bool = False) -> None: ...


class Normalizer(Protocol):
    def __call__(self, raw: dict[str, Any], *, language: str, source_url: str) -> Card: ...


@dataclass
class ReindexResult:
    updated: int = 0
    skipped: int = 0
    failed: int = 0


def reindex(
    store: ObservationStore, normalize: Normalizer, *, source: str, apply: bool = False
) -> ReindexResult:
    result = ReindexResult()
    for row in store.observations(source):
        if row["schema_version"] >= CATALOG_VERSION:
            result.skipped += 1
            continue
        try:
            card = normalize(row["raw"], language=row["language"], source_url=row["source_url"])
        except KeyError, TypeError, ValueError, ValidationError:
            result.failed += 1
            continue
        identity = ("game", "source", "source_id", "language", "set_id", "number")
        if any(getattr(card, key) != row[key] for key in identity):
            result.failed += 1
            continue
        if apply:
            store.save(
                card.model_dump(mode="json")
                | {
                    "images": row["images"],
                    "image_urls": row["image_urls"],
                    "updated_at": row["updated_at"],
                },
                preserve_updated_at=True,
            )
        result.updated += 1
    return result
