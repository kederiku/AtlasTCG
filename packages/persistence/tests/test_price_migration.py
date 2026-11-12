from datetime import UTC, datetime

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, select
from tcg_core.catalog.retention import without_prices


def test_migration_removes_existing_prices_across_batches_preserving_cards_and_images(
    tmp_path, monkeypatch
):
    url = f"sqlite:///{tmp_path / 'prices.db'}"
    monkeypatch.setenv("TCG_DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "0003")
    engine = create_engine(url)
    metadata = MetaData()
    cards = Table("cards", metadata, autoload_with=engine)
    sets = Table("localized_sets", metadata, autoload_with=engine)
    observed = datetime(2026, 1, 1, tzinfo=UTC)
    images = [{"path": "pokemon/fr/base1/4-base1.webp", "checksum": "unchanged"}]
    with engine.begin() as connection:
        connection.execute(
            sets.insert().values(
                game="pokemon",
                source="tcgdex",
                source_id="base1",
                language="fr",
                name="Set de Base",
                info={"name": "Set de Base", "raw": {"pricing": {"usd": 1}}},
            )
        )
        connection.execute(
            cards.insert(),
            [
                {
                    "game": "pokemon",
                    "source": "tcgdex",
                    "source_id": f"base1-{number}",
                    "language": "fr",
                    "name": "Dracaufeu",
                    "set_id": "base1",
                    "number": str(number),
                    "source_url": "https://example.com",
                    "image_urls": [],
                    "images": images,
                    "raw": {
                        "pricing": {"cardmarket": {"avg": 10}},
                        "retreat": 3,
                        "variants": [{"prices": {"eur": 20}, "name": "holo"}],
                    },
                    "game_data": {
                        "pokemon": {"pricing": {"usd": 4}, "thirdParty": {"cardmarket": 123}}
                    },
                    "faces": [
                        {
                            "name": "Dracaufeu",
                            "costs": {"retreat": {"value": 3}},
                            "attributes": {"market_price": 10},
                        }
                    ],
                    "legalities": {"standard": "not_legal"},
                    "illustrators": ["Mitsuhiro Arita"],
                    "updated_at": observed,
                    "schema_version": 1,
                }
                for number in range(205)
            ],
        )
    command.upgrade(config, "0004")
    with engine.connect() as connection:
        rows = connection.execute(select(cards)).mappings().all()
        assert len(rows) == 205
        for card in rows:
            for key in ("raw", "game_data", "faces", "legalities"):
                assert card[key] == without_prices(card[key])
            assert card["raw"] == {"retreat": 3, "variants": [{"name": "holo"}]}
            assert card["game_data"] == {"pokemon": {"thirdParty": {"cardmarket": 123}}}
            assert card["faces"][0]["costs"]["retreat"]["value"] == 3
            assert card["images"] == images
            assert card["updated_at"].replace(tzinfo=UTC) == observed
        assert connection.scalar(select(sets.c.info)) == {"name": "Set de Base", "raw": {}}
    engine.dispose()
