from sqlalchemy import select
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import cards, metadata


def observation(language="fr"):
    return {
        "game": "pokemon",
        "source": "tcgdex",
        "source_id": "base1-4",
        "language": language,
        "name": "Dracaufeu",
        "set_id": "base1",
        "number": "4",
        "source_url": "https://api.tcgdex.net/v2/fr/cards/base1-4",
        "image_urls": [],
        "images": [],
        "raw": {},
    }


def test_upsert_preserves_languages_and_sources(tmp_path):
    repository = Repository(f"sqlite:///{tmp_path / 'catalog.db'}")
    metadata.create_all(repository.engine)
    repository.save(observation())
    updated = observation() | {"name": "Nom corrigé"}
    repository.save(updated)
    repository.save(observation("en"))
    repository.save(observation() | {"source": "other"})
    with repository.engine.connect() as connection:
        rows = connection.execute(select(cards)).mappings().all()
    assert len(rows) == 3
    assert (
        next(row for row in rows if row["language"] == "fr" and row["source"] == "tcgdex")["name"]
        == "Nom corrigé"
    )
    repository.close()
