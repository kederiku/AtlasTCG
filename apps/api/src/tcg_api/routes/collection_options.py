"""HTTP projection of source choices, separate from collected catalog data."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from tcg_core.collections.discovery import (
    ChoiceKind,
    CollectionChoice,
    CollectionOptions,
    DiscoveryUnavailable,
)


def collection_option_routes(options: CollectionOptions) -> APIRouter:
    router = APIRouter(prefix="/api/collection-options/tcgdex")

    def choices(kind: ChoiceKind, languages: str, locale: str, block_id: str | None = None):
        try:
            return options.list(kind, languages.split(","), locale, block_id)
        except ValueError as error:
            raise HTTPException(422, "Invalid collection options") from error
        except DiscoveryUnavailable as error:
            raise HTTPException(503, "TCGdex choices are temporarily unavailable") from error

    @router.get("/blocks", response_model=list[CollectionChoice])
    def blocks(languages: str, locale: Literal["fr", "en", "es"] = "fr"):
        return choices("block", languages, locale)

    @router.get("/sets", response_model=list[CollectionChoice])
    def sets(languages: str, locale: Literal["fr", "en", "es"] = "fr", block_id: str | None = None):
        return choices("set", languages, locale, block_id)

    return router
