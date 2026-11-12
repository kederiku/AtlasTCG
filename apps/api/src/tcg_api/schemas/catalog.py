"""Explicit HTTP contracts; storage columns never define the public API implicitly."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field
from tcg_core.catalog.models import BlockInfo, CardFace, SetInfo


class CardSummary(BaseModel):
    game: str
    source: str
    source_id: str
    language: str
    name: str
    set_id: str
    set_name: str | None
    block_id: str | None = None
    block_name: str | None = None
    number: str
    source_url: str
    image_urls: list[str]
    rarity: str | None
    illustrators: list[str]
    updated_at: datetime
    schema_version: int


class CardDetail(CardSummary):
    versions: list[CardSummary] = Field(default_factory=list)
    source_image_urls: list[str]
    set_info: SetInfo
    faces: list[CardFace]
    legalities: dict[str, str]
    game_data: dict[str, Any]
    raw: dict[str, Any]


class CardPage(BaseModel):
    items: list[CardSummary]
    total: int
    page: int
    page_size: int


class CardGroup(CardSummary):
    versions: list[CardSummary]


class CardGroupPage(BaseModel):
    items: list[CardGroup]
    total: int
    page: int
    page_size: int


class BlockFacet(BaseModel):
    game: str
    source: str
    id: str
    names: dict[str, str]


class SetFacet(BlockFacet):
    block_ids: dict[str, str] = Field(default_factory=dict)


class Overview(BaseModel):
    total: int
    games: list[str]
    languages: list[str]
    sets: list[SetFacet]
    blocks: list[BlockFacet]


class BlockView(BaseModel):
    game: str
    source: str
    source_id: str
    language: str
    name: str | None
    info: BlockInfo


class SetView(BaseModel):
    game: str
    source: str
    source_id: str
    language: str
    name: str | None
    block_id: str | None = None
    block_name: str | None = None
    release_date: date | None
    info: SetInfo = Field(default_factory=SetInfo)
