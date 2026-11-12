"""Catalog persistence and engine lifecycle, delegating queries to a shared reader."""

from datetime import UTC, date, datetime

from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from tcg_core.catalog.models import (
    BlockInfo,
    Card,
    LocalizedBlock,
    LocalizedSet,
    SetInfo,
)

from tcg_persistence.catalog_reader import SqlCatalogReader
from tcg_persistence.schema import blocks, cards, sets

IDENTITY = ("game", "source", "source_id", "language")


class Repository:
    def __init__(self, url: str):
        self.engine = create_engine(url, pool_pre_ping=True)
        if self.engine.dialect.name not in {"sqlite", "postgresql"}:
            raise ValueError("Only SQLite and PostgreSQL are supported")
        if self.engine.dialect.name == "sqlite":

            @event.listens_for(self.engine, "connect")
            def foreign_keys(connection, record):
                connection.execute("PRAGMA foreign_keys=ON")

        self._reader = SqlCatalogReader(self.engine)

    def _upsert(self, connection, table, values, identity=IDENTITY):
        insert = pg_insert if self.engine.dialect.name == "postgresql" else sqlite_insert
        statement = insert(table).values(**values)
        connection.execute(
            statement.on_conflict_do_update(
                index_elements=list(identity),
                set_={key: value for key, value in values.items() if key not in identity},
            )
        )

    def contains(self, *, game, source, source_id, language):
        return self._reader.contains(
            game=game, source=source, source_id=source_id, language=language
        )

    def _save_block(self, connection, observation: LocalizedBlock):
        key = {name: getattr(observation, name) for name in IDENTITY}
        incoming = observation.info.model_dump(mode="json")
        existing = connection.execute(
            select(blocks.c.info).where(*(blocks.c[name] == value for name, value in key.items()))
        ).scalar_one_or_none()
        if existing and not observation.is_complete:
            incoming = incoming | {
                k: v for k, v in existing.items() if v is not None and k != "raw"
            }
            incoming["raw"] = observation.info.raw | existing.get("raw", {})
        self._upsert(connection, blocks, key | {"name": incoming["name"], "info": incoming})

    def save_block(self, observation: LocalizedBlock):
        with self.engine.begin() as connection:
            self._save_block(connection, observation)

    def _save_set(self, connection, observation: LocalizedSet):
        key = {name: getattr(observation, name) for name in IDENTITY}
        incoming = observation.info.model_dump(mode="json")
        existing = connection.execute(
            select(sets.c.info).where(*(sets.c[name] == value for name, value in key.items()))
        ).scalar_one_or_none()
        if existing and not observation.is_complete:
            existing = SetInfo.model_validate(existing).model_dump(mode="json")
            incoming = existing | {
                name: value
                for name, value in incoming.items()
                if value is not None and name != "raw"
            }
            incoming["raw"] = existing.get("raw", {}) | observation.info.raw
        block = incoming.get("block")
        if block:
            self._save_block(
                connection,
                LocalizedBlock(
                    game=observation.game,
                    source=observation.source,
                    source_id=block["id"],
                    language=observation.language,
                    info=BlockInfo(name=block.get("name")),
                ),
            )
        self._upsert(
            connection,
            sets,
            key
            | {
                "name": incoming["name"],
                "info": incoming,
                "block_id": block["id"] if block else None,
                "release_date": date.fromisoformat(incoming["release_date"])
                if incoming.get("release_date")
                else None,
            },
        )

    def save_set(self, observation: LocalizedSet):
        with self.engine.begin() as connection:
            self._save_set(connection, observation)

    def save(self, item: dict, *, preserve_updated_at: bool = False):
        card = Card.model_validate(
            {key: value for key, value in item.items() if key in Card.model_fields}
        )
        document = card.model_dump(mode="json")
        values = {
            column.name: document[column.name] for column in cards.c if column.name in document
        }
        values["images"] = item.get("images", [])
        values["updated_at"] = item["updated_at"] if preserve_updated_at else datetime.now(UTC)
        with self.engine.begin() as connection:
            self._save_set(
                connection,
                LocalizedSet(
                    game=card.game,
                    source=card.source,
                    source_id=card.set_id,
                    language=card.language,
                    info=card.set_info,
                ),
            )
            self._upsert(connection, cards, values)

    def close(self):
        self.engine.dispose()

    def is_ready(self) -> bool:
        try:
            self._reader.check_ready()
        except SQLAlchemyError:
            return False
        return True

    def search(
        self, *, q="", game="", source="", language="", set_id="", block_id="", page=1, page_size=24
    ):
        return self._reader.search(
            q=q,
            game=game,
            source=source,
            language=language,
            set_id=set_id,
            block_id=block_id,
            page=page,
            page_size=page_size,
        )

    def get(self, *, game, source, source_id, language):
        return self._reader.get(game=game, source=source, source_id=source_id, language=language)

    def browse(self, **filters):
        return self._reader.browse(**filters)

    def list_blocks(self):
        return self._reader.list_blocks()

    def list_sets(self):
        return self._reader.list_sets()

    def overview(self):
        return self._reader.overview()

    def observations(self, source: str, batch_size: int = 200):
        yield from self._reader.observations(source, batch_size=batch_size)
