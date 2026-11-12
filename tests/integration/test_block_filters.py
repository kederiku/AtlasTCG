import json
from pathlib import Path

from fastapi.testclient import TestClient
from tcg_api.app import create_app
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata
from tcg_scraping.sources.tcgdex.normalize import normalize_card, normalize_set


def test_catalog_filters_by_localized_block_without_merging_games_or_languages(tmp_path):
    url = f"sqlite:///{tmp_path / 'blocks.db'}"
    repository = Repository(url)
    metadata.create_all(repository.engine)
    raw = json.loads(Path("tests/fixtures/tcgdex_charizard.json").read_text())
    for game, language, set_id, block_id, block_name in [
        ("pokemon", "fr", "base1", "base", "Base"),
        ("pokemon", "fr", "base2", "base", "Base"),
        ("pokemon", "en", "base1", "base", "Base series"),
        ("pokemon", "fr", "swsh1", "swsh", "Épée et Bouclier"),
        ("magic", "fr", "base1", "base", "Autre bloc"),
        ("yugioh", "fr", "starter", None, None),
    ]:
        card = normalize_card(
            raw | {"id": f"{set_id}-4", "set": {"id": set_id, "name": set_id}},
            language=language,
            source_url="https://example.com/card",
        )
        card.game = game
        repository.save(card.model_dump(mode="json") | {"images": []})
        extension = normalize_set(
            {
                "id": set_id,
                "name": set_id,
                "serie": {"id": block_id, "name": block_name} if block_id else None,
            },
            language=language,
        )
        extension.game = game
        repository.save_set(extension)
    with TestClient(create_app(url, tmp_path / "images", tmp_path / "jobs")) as client:
        response = client.get(
            "/api/cards",
            params={"game": "pokemon", "source": "tcgdex", "language": "fr", "block_id": "base"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 2
        assert {card["set_id"] for card in result["items"]} == {"base1", "base2"}
        assert all(card["block_name"] == "Base" for card in result["items"])
        detail = client.get(
            "/api/cards/detail",
            params={
                "game": "pokemon",
                "source": "tcgdex",
                "source_id": "base1-4",
                "language": "en",
            },
        ).json()
        assert detail["set_info"]["block"] == {"id": "base", "name": "Base series"}
        overview = client.get("/api/overview").json()
        pokemon_base = next(
            block
            for block in overview["blocks"]
            if block["game"] == "pokemon" and block["id"] == "base"
        )
        assert pokemon_base["names"] == {"fr": "Base", "en": "Base series"}
        blocks = client.get("/api/blocks").json()
        assert len(blocks) == 4  # Two FR Pokemon blocks, one EN, one other game.
        assert (
            client.get("/api/cards", params={"game": "yugioh"}).json()["items"][0]["block_id"]
            is None
        )
    repository.close()
