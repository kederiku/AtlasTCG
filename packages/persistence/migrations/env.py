from pathlib import Path

from alembic import context
from sqlalchemy import create_engine
from tcg_persistence import jobs  # noqa: F401
from tcg_persistence.configuration import database_url as configured_database_url
from tcg_persistence.schema import metadata

url = configured_database_url()
if url == "sqlite:///data/catalog.db":
    Path("data").mkdir(exist_ok=True)
engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
