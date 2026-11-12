"""HTTP catalog queries and their response presentation."""

from fastapi import APIRouter, HTTPException, Query
from tcg_core.catalog.queries import CatalogService

from tcg_api.presentation.catalog import present_card, present_page
from tcg_api.schemas.catalog import (
    BlockView,
    CardDetail,
    CardGroupPage,
    CardPage,
    Overview,
    SetView,
)


def catalog_routes(service: CatalogService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/card-groups", response_model=CardGroupPage)
    def browse_cards(
        q: str = Query("", max_length=200),
        game: str = "",
        source: str = "",
        language: str = "",
        set_id: str = "",
        block_id: str = "",
        display_language: str = "fr",
        page: int = Query(1, ge=1),
        page_size: int = Query(24, ge=1, le=100),
    ):
        return present_page(
            service.browse(
                q=q,
                game=game,
                source=source,
                language=language,
                set_id=set_id,
                block_id=block_id,
                display_language=display_language,
                page=page,
                page_size=page_size,
            )
        )

    @router.get("/api/cards", response_model=CardPage)
    def list_cards(
        q: str = Query("", max_length=200),
        game: str = "",
        source: str = "",
        language: str = "",
        set_id: str = "",
        block_id: str = "",
        page: int = Query(1, ge=1),
        page_size: int = Query(24, ge=1, le=100),
    ):
        return present_page(
            service.search(
                q=q,
                game=game,
                source=source,
                language=language,
                set_id=set_id,
                block_id=block_id,
                page=page,
                page_size=page_size,
            )
        )

    @router.get("/api/cards/detail", response_model=CardDetail)
    def card_detail(game: str, source: str, source_id: str, language: str):
        result = service.detail(game=game, source=source, source_id=source_id, language=language)
        if result is None:
            raise HTTPException(404, "Card not found")
        return present_card(result)

    @router.get("/api/sets", response_model=list[SetView])
    def list_sets():
        return service.sets()

    @router.get("/api/blocks", response_model=list[BlockView])
    def list_blocks():
        return service.blocks()

    @router.get("/api/overview", response_model=Overview)
    def overview():
        return service.overview()

    return router
