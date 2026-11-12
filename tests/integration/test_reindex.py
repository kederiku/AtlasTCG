import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine
from tcg_core.catalog.models import CATALOG_VERSION
from tcg_core.catalog.reindex import reindex
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata
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


@pytest.fixture
def legacy_catalog(tmp_path):
    repository = Repository(f"sqlite:///{tmp_path / 'reindex.db'}")
    metadata.create_all(repository.engine)
    raw = json.loads(Path("tests/fixtures/tcgdex_charizard.json").read_text())
    for number in ("4", "5"):
        source = raw | {"id": f"base1-{number}", "localId": number}
        card = normalize_card(source, language="fr", source_url="https://example.com/card")
        repository.save(
            card.model_dump(mode="json")
            | {
                "schema_version": 0,
                "images": [{"path": f"pokemon/fr/base1/{number}-base1.webp"}],
                "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
            },
            preserve_updated_at=True,
        )
    try:
        yield repository
    finally:
        repository.close()


@pytest.mark.parametrize(
    "invalid_raw",
    [
        {},
        {"id": "base1-4", "name": "Dracaufeu", "localId": "4", "set": None},
        {"id": "base1-4", "name": None, "localId": "4", "set": {"id": "base1"}},
    ],
    ids=["missing-field", "invalid-source-shape", "invalid-domain-value"],
)
def test_reindex_preserves_invalid_observation_and_continues(legacy_catalog, invalid_raw):
    repository = legacy_catalog
    key = dict(game="pokemon", source="tcgdex", source_id="base1-4", language="fr")
    original = repository.get(**key)
    repository.save(
        original | {"raw": invalid_raw},
        preserve_updated_at=True,
    )
    before = repository.get(**key)

    result = reindex(repository, normalize_card, source="tcgdex", apply=True)

    assert (result.updated, result.skipped, result.failed) == (1, 0, 1)
    assert repository.get(**key) == before
    assert not repository.contains(**key)
    following = repository.get(**(key | {"source_id": "base1-5"}))
    assert following["schema_version"] == CATALOG_VERSION
    assert following["images"] == [{"path": "pokemon/fr/base1/5-base1.webp"}]
    assert following["updated_at"] == before["updated_at"]


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("game", "other"),
        ("source", "other"),
        ("source_id", "base1-99"),
        ("language", "en"),
        ("set_id", "other"),
        ("number", "004"),
    ],
)
def test_reindex_refuses_changed_identity_and_continues(legacy_catalog, field, changed):
    repository = legacy_catalog
    key = dict(game="pokemon", source="tcgdex", source_id="base1-4", language="fr")
    before = repository.get(**key)

    def changed_identity(raw, *, language, source_url):
        card = normalize_card(raw, language=language, source_url=source_url)
        if raw["id"] == "base1-4":
            return card.model_copy(update={field: changed})
        return card

    result = reindex(repository, changed_identity, source="tcgdex", apply=True)

    assert (result.updated, result.skipped, result.failed) == (1, 0, 1)
    assert repository.get(**key) == before
    assert not repository.contains(**key)
    assert repository.contains(**(key | {"source_id": "base1-5"}))
    assert repository.search()["total"] == 2
