"""Relational identities plus validated versioned documents (JSONB on PostgreSQL)."""

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import JSONB

DOCUMENT = JSON().with_variant(JSONB(), "postgresql")
metadata = MetaData()
blocks = Table(
    "localized_blocks",
    metadata,
    Column("game", String, primary_key=True),
    Column("source", String, primary_key=True),
    Column("source_id", String, primary_key=True),
    Column("language", String, primary_key=True),
    Column("name", String, nullable=True),
    Column("info", DOCUMENT, nullable=False),
)
sets = Table(
    "localized_sets",
    metadata,
    Column("game", String, primary_key=True),
    Column("source", String, primary_key=True),
    Column("source_id", String, primary_key=True),
    Column("language", String, primary_key=True),
    Column("name", String, nullable=True),
    Column("release_date", Date, nullable=True),
    Column("info", DOCUMENT, nullable=False),
    Column("block_id", String, nullable=True),
    ForeignKeyConstraint(
        ["game", "source", "block_id", "language"],
        [
            "localized_blocks.game",
            "localized_blocks.source",
            "localized_blocks.source_id",
            "localized_blocks.language",
        ],
        name="fk_sets_localized_block",
    ),
    Index("ix_sets_block_identity", "game", "source", "block_id", "language"),
)
cards = Table(
    "cards",
    metadata,
    Column("game", String, primary_key=True),
    Column("source", String, primary_key=True),
    Column("source_id", String, primary_key=True),
    Column("language", String, primary_key=True),
    Column("name", String, nullable=False, index=True),
    Column("set_id", String, nullable=False, index=True),
    Column("number", String, nullable=False),
    Column("source_url", String, nullable=False),
    Column("image_urls", JSON, nullable=False),
    Column("images", JSON, nullable=False),
    Column("raw", JSON, nullable=False),
    Column("rarity", String, nullable=True),
    Column("illustrators", DOCUMENT, nullable=False, server_default="[]"),
    Column("faces", DOCUMENT, nullable=False, server_default="[]"),
    Column("legalities", DOCUMENT, nullable=False, server_default="{}"),
    Column("game_data", DOCUMENT, nullable=False, server_default="{}"),
    Column("schema_version", Integer, nullable=False, server_default="0"),
    ForeignKeyConstraint(
        ["game", "source", "set_id", "language"],
        [
            "localized_sets.game",
            "localized_sets.source",
            "localized_sets.source_id",
            "localized_sets.language",
        ],
        name="fk_cards_localized_set",
    ),
    Index("ix_cards_set_identity", "game", "source", "set_id", "language"),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
