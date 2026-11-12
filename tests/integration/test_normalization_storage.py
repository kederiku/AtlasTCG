import json
from pathlib import Path

from tcg_scraping.sources.tcgdex.normalize import normalize_card


def test_partial_set_observation_does_not_erase_full_metadata(tmp_path):
    from tcg_persistence.catalog import Repository
    from tcg_persistence.schema import metadata
    from tcg_scraping.sources.tcgdex.normalize import normalize_set

    repository = Repository(f"sqlite:///{tmp_path / 'catalog.db'}")
    metadata.create_all(repository.engine)
    repository.save_set(
        normalize_set(
            {
                "id": "base1",
                "name": "Set de Base",
                "releaseDate": "1999-11-18",
                "serie": {"id": "base", "name": "Base"},
                "cardCount": {"official": 102, "total": 102},
            },
            language="fr",
        )
    )
    raw = json.loads(Path("tests/fixtures/tcgdex_charizard.json").read_text())
    repository.save(
        normalize_card(raw, language="fr", source_url="https://example.com").model_dump(mode="json")
        | {"images": []}
    )
    card = repository.get(game="pokemon", source="tcgdex", source_id="base1-4", language="fr")
    assert card["set_info"]["release_date"] == "1999-11-18"
    assert card["set_info"]["block"] == {"id": "base", "name": "Base"}
    assert repository.search()["items"][0]["set_name"] == "Set de Base"
    assert "raw" not in repository.search()["items"][0]
    assert "faces" not in repository.search()["items"][0]
    repository.close()
