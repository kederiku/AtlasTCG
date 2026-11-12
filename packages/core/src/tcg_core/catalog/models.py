"""Versioned, game-independent contract for a localized printing.

Null means unknown/not supplied, never zero. Printed symbolic values remain strings.
Game rules are data: this catalog does not attempt to interpret a game's engine.
"""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from tcg_core.catalog.retention import without_prices

CATALOG_VERSION = 2


class ValueObject(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResourceCost(ValueObject):
    symbols: list[str] | None = None
    value: int | float | str | None = None
    text: str | None = None


class TextBlock(ValueObject):
    kind: str
    text: str


class Ability(ValueObject):
    kind: str
    name: str | None = None
    text: str | None = None
    cost: ResourceCost | None = None
    damage: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class CardFace(ValueObject):
    name: str
    types: list[str] = Field(default_factory=list)
    traits: dict[str, list[str]] = Field(default_factory=dict)
    texts: list[TextBlock] = Field(default_factory=list)
    statistics: dict[str, int | float | str] = Field(default_factory=dict)
    costs: dict[str, ResourceCost] = Field(default_factory=dict)
    abilities: list[Ability] = Field(default_factory=list)
    illustrators: list[str] = Field(default_factory=list)
    image_index: int | None = Field(default=None, ge=0)


class BlockReference(ValueObject):
    id: str = Field(min_length=1)
    name: str | None = None


class BlockInfo(ValueObject):
    @model_validator(mode="before")
    @classmethod
    def exclude_prices(cls, data: Any) -> Any:
        return without_prices(data)

    name: str | None = None
    logo_url: HttpUrl | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class LocalizedBlock(ValueObject):
    kind: Literal["block"] = "block"
    game: str
    source: str
    source_id: str = Field(min_length=1)
    language: str
    info: BlockInfo
    is_complete: bool = False


class SetInfo(ValueObject):
    @model_validator(mode="before")
    @classmethod
    def exclude_prices(cls, data: Any) -> Any:
        data = without_prices(data)
        if isinstance(data, dict):
            # Accept pre-v2 observations at the ingestion boundary during reindexing.
            old_id = data.pop("series_id", None)
            old_name = data.pop("series_name", None)
            if "block" not in data and old_id:
                data["block"] = {"id": old_id, "name": old_name}
        return data

    name: str | None = None
    block: BlockReference | None = None
    release_date: date | None = None
    official_count: int | None = Field(default=None, ge=0)
    total_count: int | None = Field(default=None, ge=0)
    logo_url: HttpUrl | None = None
    symbol_url: HttpUrl | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class LocalizedSet(ValueObject):
    kind: Literal["set"] = "set"
    game: str
    source: str
    source_id: str
    language: str
    info: SetInfo
    # Full set response is authoritative; card-embedded summaries are partial.
    is_complete: bool = False


class Card(ValueObject):
    @model_validator(mode="before")
    @classmethod
    def exclude_prices(cls, data: Any) -> Any:
        return without_prices(data)

    kind: Literal["card"] = "card"
    game: str = Field(pattern=r"^[a-z0-9-]+$")
    source: str = Field(pattern=r"^[a-z0-9-]+$")
    source_id: str = Field(min_length=1)
    language: str = Field(pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]+)*$")
    name: str = Field(min_length=1)
    set_id: str = Field(min_length=1)
    number: str = Field(min_length=1)
    source_url: HttpUrl
    image_urls: list[HttpUrl] = Field(default_factory=list)
    set_info: SetInfo = Field(default_factory=SetInfo)
    rarity: str | None = None
    illustrators: list[str] = Field(default_factory=list)
    faces: list[CardFace] = Field(default_factory=list)
    legalities: dict[str, str] = Field(default_factory=dict)
    game_data: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = Field(default=CATALOG_VERSION, ge=0)
    raw: dict[str, Any] = Field(default_factory=dict)
