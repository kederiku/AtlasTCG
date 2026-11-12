from tcg_persistence.catalog import Repository


def test_existing_series_become_blocks_without_changing_card_observations(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import MetaData, Table, create_engine, inspect, select

    url = f"sqlite:///{tmp_path / 'upgrade.db'}"
    monkeypatch.setenv("TCG_DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "0004")
    engine = create_engine(url)
    legacy_sets = Table("localized_sets", MetaData(), autoload_with=engine)
    legacy_cards = Table("cards", MetaData(), autoload_with=engine)
    with engine.begin() as connection:
        for language, name in [("fr", "Base"), ("en", "Base series")]:
            for number in range(205):
                connection.execute(
                    legacy_sets.insert().values(
                        game="pokemon",
                        source="tcgdex",
                        source_id=f"base{number}",
                        language=language,
                        name="Base Set",
                        info={
                            "name": "Base Set",
                            "series_id": "base",
                            "series_name": name,
                            "raw": {"serie": {"id": "base", "name": name}},
                        },
                    )
                )
        connection.execute(
            legacy_sets.insert().values(
                game="yugioh",
                source="source",
                source_id="standalone",
                language="fr",
                name="Standalone",
                info={},
            )
        )
        connection.execute(
            legacy_cards.insert().values(
                game="pokemon",
                source="tcgdex",
                source_id="base1-4",
                language="fr",
                name="Dracaufeu",
                set_id="base1",
                number="004",
                source_url="https://example.com",
                image_urls=[],
                images=[{"path": "pokemon/fr/base1/004-base1.webp"}],
                raw={"original": True},
                schema_version=1,
                updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        before = dict(connection.execute(select(legacy_cards)).mappings().one())
    command.upgrade(config, "head")
    assert inspect(engine).has_table("localized_blocks")
    repository = Repository(url)
    assert len(repository.list_blocks()) == 2
    assert len(repository.list_sets()) == 411
    card = repository.get(game="pokemon", source="tcgdex", source_id="base1-4", language="fr")
    assert card["set_info"]["block"] == {"id": "base", "name": "Base"}
    assert card["block_id"] == "base"
    with engine.connect() as connection:
        assert dict(connection.execute(select(legacy_cards)).mappings().one()) == before
    assert next(s for s in repository.list_sets() if s["game"] == "yugioh")["block_id"] is None
    command.check(config)
    repository.close()
    engine.dispose()
