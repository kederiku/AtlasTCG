"""Promote optional series metadata into localized blocks and set relationships.

The backfill is frozen and reads existing set documents only. Card observations,
images, timestamps and schema versions are left unchanged.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _batches(bind, table):
    identity = list(table.primary_key.columns)
    last = None
    while True:
        query = sa.select(table).order_by(*identity).limit(200)
        if last is not None:
            query = query.where(sa.tuple_(*identity) > last)
        rows = bind.execute(query).mappings().all()
        if not rows:
            return
        yield from rows
        last = tuple(rows[-1][column.name] for column in identity)


def upgrade():
    document = sa.JSON().with_variant(JSONB(), "postgresql")
    blocks = op.create_table(
        "localized_blocks",
        sa.Column("game", sa.String(), primary_key=True),
        sa.Column("source", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), primary_key=True),
        sa.Column("language", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("info", document, nullable=False),
    )
    op.add_column("localized_sets", sa.Column("block_id", sa.String(), nullable=True))
    bind = op.get_bind()
    sets = sa.Table("localized_sets", sa.MetaData(), autoload_with=bind)
    identity = list(sets.primary_key.columns)
    insert = pg_insert if bind.dialect.name == "postgresql" else sqlite_insert
    for row in _batches(bind, sets):
        info = dict(row["info"])
        raw = info.get("raw") or {}
        series = raw.get("serie") or {}
        block = info.get("block") or {}
        block_id = block.get("id") or info.get("series_id") or series.get("id")
        name = block.get("name") or info.get("series_name") or series.get("name")
        info.pop("series_id", None)
        info.pop("series_name", None)
        info["block"] = {"id": block_id, "name": name} if block_id else None
        if block_id:
            key = {field: row[field] for field in ("game", "source", "language")}
            key["source_id"] = block_id
            statement = insert(blocks).values(
                **key,
                name=name,
                info={
                    "name": name,
                    "logo_url": None,
                    "raw": series,
                },
            )
            bind.execute(
                statement.on_conflict_do_nothing(
                    index_elements=[c.name for c in blocks.primary_key]
                )
            )
            # A nameless first summary must not prevent a later named summary from filling it.
            bind.execute(
                blocks.update()
                .where(*(blocks.c[k] == v for k, v in key.items()), blocks.c.name.is_(None))
                .values(name=name, info={"name": name, "logo_url": None, "raw": series})
            )
        bind.execute(
            sets.update()
            .where(*(column == row[column.name] for column in identity))
            .values(block_id=block_id, info=info)
        )
    with op.batch_alter_table("localized_sets") as batch:
        batch.create_foreign_key(
            "fk_sets_localized_block",
            "localized_blocks",
            ["game", "source", "block_id", "language"],
            ["game", "source", "source_id", "language"],
        )
        batch.create_index("ix_sets_block_identity", ["game", "source", "block_id", "language"])


def downgrade():
    bind = op.get_bind()
    sets = sa.Table("localized_sets", sa.MetaData(), autoload_with=bind)
    identity = list(sets.primary_key.columns)
    for row in _batches(bind, sets):
        info = dict(row["info"])
        block = info.pop("block", None) or {}
        info["series_id"] = block.get("id")
        info["series_name"] = block.get("name")
        bind.execute(
            sets.update()
            .where(*(column == row[column.name] for column in identity))
            .values(info=info)
        )
    with op.batch_alter_table("localized_sets") as batch:
        batch.drop_index("ix_sets_block_identity")
        batch.drop_constraint("fk_sets_localized_block", type_="foreignkey")
        batch.drop_column("block_id")
    op.drop_table("localized_blocks")
