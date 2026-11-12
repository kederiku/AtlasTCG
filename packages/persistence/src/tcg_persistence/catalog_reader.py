"""SQL catalog queries using a shared engine owned by the repository."""

from sqlalchemy import and_, func, or_, select, true, tuple_
from sqlalchemy.engine import Engine
from tcg_core.catalog.models import CATALOG_VERSION, SetInfo

from tcg_persistence.schema import blocks, cards, sets

IDENTITY = ("game", "source", "source_id", "language")
SET_JOIN = and_(
    cards.c.game == sets.c.game,
    cards.c.source == sets.c.source,
    cards.c.set_id == sets.c.source_id,
    cards.c.language == sets.c.language,
)
BLOCK_JOIN = and_(
    sets.c.game == blocks.c.game,
    sets.c.source == blocks.c.source,
    sets.c.block_id == blocks.c.source_id,
    sets.c.language == blocks.c.language,
)
CATALOG_JOIN = cards.outerjoin(sets, SET_JOIN).outerjoin(blocks, BLOCK_JOIN)
BLOCK_COLUMNS = [sets.c.block_id, blocks.c.name.label("block_name")]
SUMMARY_COLUMNS = [
    column for column in cards.c if column.name not in {"raw", "faces", "game_data", "legalities"}
]


class SqlCatalogReader:
    def __init__(self, engine: Engine):
        self.engine = engine

    def contains(self, *, game, source, source_id, language):
        statement = select(cards.c.source_id).where(
            cards.c.game == game,
            cards.c.source == source,
            cards.c.source_id == source_id,
            cards.c.language == language,
            cards.c.schema_version >= CATALOG_VERSION,
        )
        with self.engine.connect() as connection:
            return connection.execute(statement).first() is not None

    def check_ready(self):
        with self.engine.connect() as connection:
            connection.execute(select(cards.c.source_id).limit(1))

    def search(
        self, *, q="", game="", source="", language="", set_id="", block_id="", page=1, page_size=24
    ):
        filters = [
            cards.c[key] == value
            for key, value in [
                ("game", game),
                ("source", source),
                ("language", language),
                ("set_id", set_id),
            ]
            if value
        ]
        if block_id:
            filters.append(sets.c.block_id == block_id)
        if q:
            filters.append(cards.c.name.icontains(q, autoescape=True))
        with self.engine.connect() as connection:
            total = connection.scalar(
                select(func.count()).select_from(CATALOG_JOIN).where(*filters)
            )
            items = (
                connection.execute(
                    select(*SUMMARY_COLUMNS, sets.c.name.label("set_name"), *BLOCK_COLUMNS)
                    .select_from(CATALOG_JOIN)
                    .where(*filters)
                    .order_by(
                        cards.c.game,
                        cards.c.source,
                        cards.c.set_id,
                        cards.c.number,
                        cards.c.language,
                        cards.c.source_id,
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
                .mappings()
                .all()
            )
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get(self, *, game, source, source_id, language):
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(
                        cards,
                        sets.c.name.label("set_name"),
                        sets.c.info.label("set_info"),
                        *BLOCK_COLUMNS,
                    )
                    .select_from(CATALOG_JOIN)
                    .where(
                        cards.c.game == game,
                        cards.c.source == source,
                        cards.c.source_id == source_id,
                        cards.c.language == language,
                    )
                )
                .mappings()
                .first()
            )
            if not row:
                return None
            result = dict(row)
            result["set_info"] = self._set_info(row["set_info"], row["block_id"], row["block_name"])
            result["versions"] = [
                dict(version)
                for version in connection.execute(
                    select(*SUMMARY_COLUMNS, sets.c.name.label("set_name"), *BLOCK_COLUMNS)
                    .select_from(CATALOG_JOIN)
                    .where(
                        cards.c.game == game,
                        cards.c.source == source,
                        cards.c.source_id == source_id,
                    )
                    .order_by(cards.c.language)
                ).mappings()
            ]
            return result

    def browse(
        self, *, q="", game="", source="", language="", set_id="", block_id="", page=1, page_size=24
    ):
        filters = [true()]
        for key, value in [
            ("game", game),
            ("source", source),
            ("language", language),
            ("set_id", set_id),
        ]:
            if value:
                filters.append(cards.c[key] == value)
        if block_id:
            filters.append(sets.c.block_id == block_id)
        if q:
            translations = cards.alias("card_translations")
            set_names = sets.alias("set_translations")
            block_names = blocks.alias("block_translations")
            translated_set = (
                select(set_names.c.source_id)
                .where(
                    set_names.c.game == translations.c.game,
                    set_names.c.source == translations.c.source,
                    set_names.c.source_id == translations.c.set_id,
                    or_(
                        set_names.c.name.icontains(q, autoescape=True),
                        select(block_names.c.source_id)
                        .where(
                            block_names.c.game == set_names.c.game,
                            block_names.c.source == set_names.c.source,
                            block_names.c.source_id == set_names.c.block_id,
                            block_names.c.name.icontains(q, autoescape=True),
                        )
                        .exists(),
                    ),
                )
                .exists()
            )
            filters.append(
                select(translations.c.source_id)
                .where(
                    translations.c.game == cards.c.game,
                    translations.c.source == cards.c.source,
                    translations.c.source_id == cards.c.source_id,
                    or_(translations.c.name.icontains(q, autoescape=True), translated_set),
                )
                .exists()
            )
        identity = [cards.c.game, cards.c.source, cards.c.source_id]
        # Eligibility is per printing; ordering is computed over all versions so
        # changing the display language cannot reorder or split groups.
        eligible = select(*identity).select_from(CATALOG_JOIN).where(*filters).distinct()
        ordering = (
            select(
                *identity,
                func.min(cards.c.set_id).label("set_order"),
                func.min(cards.c.number).label("number_order"),
            )
            .where(tuple_(*identity).in_(eligible))
            .group_by(*identity)
        ).subquery()
        with self.engine.connect() as connection:
            total = connection.scalar(select(func.count()).select_from(ordering))
            keys = list(
                connection.execute(
                    select(ordering.c.game, ordering.c.source, ordering.c.source_id)
                    .order_by(
                        ordering.c.game,
                        ordering.c.source,
                        ordering.c.set_order,
                        ordering.c.number_order,
                        ordering.c.source_id,
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            grouped = {tuple(key): {"versions": [], "matching_languages": []} for key in keys}
            if keys:
                rows = connection.execute(
                    select(
                        *SUMMARY_COLUMNS,
                        sets.c.name.label("set_name"),
                        *BLOCK_COLUMNS,
                        and_(*filters).label("matches_filters"),
                    )
                    .select_from(CATALOG_JOIN)
                    .where(tuple_(*identity).in_(keys))
                    .order_by(*identity, cards.c.language)
                ).mappings()
                for row in rows:
                    item = dict(row)
                    matches = item.pop("matches_filters")
                    group = grouped[(item["game"], item["source"], item["source_id"])]
                    group["versions"].append(item)
                    if matches:
                        group["matching_languages"].append(item["language"])
        return {
            "items": list(grouped.values()),
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def _set_info(info, block_id, block_name):
        return SetInfo.model_validate(info).model_dump(mode="json") | {
            "block": {"id": block_id, "name": block_name} if block_id else None,
        }

    def list_blocks(self):
        with self.engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(blocks).order_by(
                        blocks.c.game, blocks.c.source, blocks.c.source_id, blocks.c.language
                    )
                ).mappings()
            ]

    def list_sets(self):
        with self.engine.connect() as connection:
            return [
                dict(row)
                | {"info": self._set_info(row["info"], row["block_id"], row["block_name"])}
                for row in connection.execute(
                    select(sets, blocks.c.name.label("block_name"))
                    .select_from(sets.outerjoin(blocks, BLOCK_JOIN))
                    .order_by(sets.c.game, sets.c.source, sets.c.source_id, sets.c.language)
                ).mappings()
            ]

    def overview(self):
        with self.engine.connect() as connection:
            total = connection.scalar(select(func.count()).select_from(cards))
            facets = {
                key: list(
                    connection.scalars(select(cards.c[key]).distinct().order_by(cards.c[key]))
                )
                for key in ("game", "language")
            }
            set_rows = (
                connection.execute(
                    select(
                        sets.c.game,
                        sets.c.source,
                        sets.c.source_id,
                        sets.c.language,
                        sets.c.name,
                        sets.c.block_id,
                    ).order_by(sets.c.game, sets.c.source, sets.c.source_id, sets.c.language)
                )
                .mappings()
                .all()
            )
            block_rows = (
                connection.execute(
                    select(
                        blocks.c.game,
                        blocks.c.source,
                        blocks.c.source_id,
                        blocks.c.language,
                        blocks.c.name,
                    ).order_by(
                        blocks.c.game, blocks.c.source, blocks.c.source_id, blocks.c.language
                    )
                )
                .mappings()
                .all()
            )
        grouped = {}
        for row in set_rows:
            key = (row["game"], row["source"], row["source_id"])
            item = grouped.setdefault(
                key, {"game": key[0], "source": key[1], "id": key[2], "names": {}, "block_ids": {}}
            )
            if row["name"]:
                item["names"][row["language"]] = row["name"]
            if row["block_id"]:
                item["block_ids"][row["language"]] = row["block_id"]
        grouped_blocks = {}
        for row in block_rows:
            key = (row["game"], row["source"], row["source_id"])
            item = grouped_blocks.setdefault(
                key,
                {
                    "game": key[0],
                    "source": key[1],
                    "id": key[2],
                    "names": {},
                },
            )
            if row["name"]:
                item["names"][row["language"]] = row["name"]
        return {
            "total": total,
            "games": facets["game"],
            "languages": facets["language"],
            "sets": list(grouped.values()),
            "blocks": list(grouped_blocks.values()),
        }

    def observations(self, source: str, batch_size: int = 200):
        last = None
        columns = [cards.c[name] for name in IDENTITY]
        while True:
            statement = (
                select(cards).where(cards.c.source == source).order_by(*columns).limit(batch_size)
            )
            if last:
                statement = statement.where(tuple_(*columns) > last)
            with self.engine.connect() as connection:
                batch = connection.execute(statement).mappings().all()
            if not batch:
                break
            for row in batch:
                yield dict(row)
            last = tuple(batch[-1][key] for key in IDENTITY)
