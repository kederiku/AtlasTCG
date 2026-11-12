import json
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine
from tcg_core.catalog.reindex import reindex
from tcg_persistence.catalog import Repository
from tcg_scraping.sources.tcgdex.normalize import normalize_card


def test_upgrade_and_offline_reindex_preserve_observation_and_images(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'old.db'}"
    monkeypatch.setenv("TCG_DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "0002")
    engine = create_engine(url)
    legacy = Table("cards", MetaData(), autoload_with=engine)
    raw = json.loads(Path("tests/fixtures/tcgdex_charizard.json").read_text())
    observed = datetime(2026, 1, 1, tzinfo=UTC)
    images = [{"path": "pokemon/fr/base1/4-base1.webp", "checksum": "unchanged"}]
    with engine.begin() as connection:
        connection.execute(
            legacy.insert().values(
                game="pokemon",
                source="tcgdex",
                source_id="base1-4",
                language="fr",
                name=raw["name"],
                set_id="base1",
                number="4",
                source_url="https://example.com/card",
                image_urls=[],
                images=images,
                raw=raw,
                updated_at=observed,
            )
        )
    engine.dispose()
    command.upgrade(config, "head")
    repository = Repository(url)
    key = dict(game="pokemon", source="tcgdex", source_id="base1-4", language="fr")
    assert not repository.contains(**key)
    assert reindex(repository, normalize_card, source="tcgdex").updated == 1
    assert not repository.contains(**key)
    assert reindex(repository, normalize_card, source="tcgdex", apply=True).updated == 1
    card = repository.get(**key)
    assert repository.contains(**key)
    assert card["set_name"] == "Set de Base"
    assert card["raw"] == raw
    assert card["images"] == images
    assert card["updated_at"].replace(tzinfo=UTC) == observed
    assert reindex(repository, normalize_card, source="tcgdex", apply=True).skipped == 1
    command.check(config)
    repository.close()
