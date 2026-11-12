"""Catalog use cases and read ports, independent of HTTP and SQL."""

from typing import Any, Protocol, TypedDict, Unpack

from tcg_core.catalog.navigation import preferred_language

CatalogDocument = dict[str, Any]


class CatalogFilters(TypedDict, total=False):
    q: str
    game: str
    source: str
    language: str
    set_id: str
    block_id: str
    page: int
    page_size: int


class CardIdentity(TypedDict):
    game: str
    source: str
    source_id: str
    language: str


class GroupCandidates(TypedDict):
    versions: list[CatalogDocument]
    matching_languages: list[str]


class GroupCandidatePage(TypedDict):
    items: list[GroupCandidates]
    total: int
    page: int
    page_size: int


class CatalogReader(Protocol):
    def browse(self, **filters: Unpack[CatalogFilters]) -> GroupCandidatePage: ...
    def search(
        self,
        *,
        q: str = "",
        game: str = "",
        source: str = "",
        language: str = "",
        set_id: str = "",
        block_id: str = "",
        page: int = 1,
        page_size: int = 24,
    ) -> CatalogDocument: ...
    def overview(self) -> CatalogDocument: ...
    def get(
        self, *, game: str, source: str, source_id: str, language: str
    ) -> CatalogDocument | None: ...
    def list_sets(self) -> list[CatalogDocument]: ...
    def list_blocks(self) -> list[CatalogDocument]: ...


class CatalogService:
    def __init__(self, reader: CatalogReader) -> None:
        self.reader = reader

    def search(self, **filters: Unpack[CatalogFilters]) -> CatalogDocument:
        return self.reader.search(**filters)

    def browse(
        self, *, display_language: str = "fr", **filters: Unpack[CatalogFilters]
    ) -> CatalogDocument:
        page = self.reader.browse(**filters)
        items = []
        for group in page["items"]:
            language = preferred_language(group["matching_languages"], display_language)
            representative = next(v for v in group["versions"] if v["language"] == language)
            items.append(representative | {"versions": group["versions"]})
        return dict(page) | {"items": items}

    def overview(self) -> CatalogDocument:
        return self.reader.overview()

    def detail(self, **identity: Unpack[CardIdentity]) -> CatalogDocument | None:
        return self.reader.get(**identity)

    def sets(self) -> list[CatalogDocument]:
        return self.reader.list_sets()

    def blocks(self) -> list[CatalogDocument]:
        return self.reader.list_blocks()
