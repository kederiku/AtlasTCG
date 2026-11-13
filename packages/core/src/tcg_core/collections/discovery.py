"""Prepare source choices without adding observations to the local catalog."""

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from tcg_core.catalog.navigation import preferred_language
from tcg_core.collections.models import CollectionParameters, CollectionScope

ChoiceKind = Literal["block", "set"]


class LocalizedChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
    name: str = Field(min_length=1)
    language: str


class CollectionChoice(BaseModel):
    id: str
    name: str
    languages: list[str]


class DiscoveryUnavailable(Exception):
    """Source choices could not be retrieved completely."""


class CollectionDiscovery(Protocol):
    def choices(
        self, kind: ChoiceKind, languages: list[str], block_id: str | None
    ) -> list[LocalizedChoice]: ...


class CollectionOptions:
    def __init__(self, discovery: CollectionDiscovery) -> None:
        self.discovery = discovery

    def list(
        self, kind: ChoiceKind, languages: list[str], locale: str, block_id: str | None = None
    ) -> list[CollectionChoice]:
        requested = CollectionParameters(languages=languages).languages
        if locale not in {"fr", "en", "es"}:
            raise ValueError("Unsupported interface language")
        if block_id is not None:
            CollectionScope(kind="block", id=block_id)
        lookup_languages = list(dict.fromkeys([*requested, locale, "fr", "en"]))
        groups: dict[str, dict[str, LocalizedChoice]] = {}
        for choice in self.discovery.choices(kind, lookup_languages, block_id):
            groups.setdefault(choice.id, {})[choice.language] = choice
        result = []
        for identifier, versions in groups.items():
            available = sorted(set(requested).intersection(versions))
            if available:
                name = versions[preferred_language(versions, locale)].name
                result.append(CollectionChoice(id=identifier, name=name, languages=available))
        return sorted(result, key=lambda choice: (choice.name.casefold(), choice.id))
