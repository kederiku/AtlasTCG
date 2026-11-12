"""Shared connection configuration for HTTP, workers, spiders and migrations."""

import os

from sqlalchemy.engine import URL


def database_url() -> str:
    if explicit := os.getenv("TCG_DATABASE_URL"):
        return explicit
    if host := os.getenv("POSTGRES_HOST"):
        return URL.create(
            "postgresql+psycopg",
            username=os.getenv("POSTGRES_USER", "tcg"),
            password=os.environ["POSTGRES_PASSWORD"],
            host=host,
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "tcg"),
        ).render_as_string(hide_password=False)
    return "sqlite:///data/catalog.db"
