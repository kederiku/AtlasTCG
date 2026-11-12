import json
from pathlib import Path

from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when
from tcg_api.app import create_app
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata
from tcg_scraping.sources.tcgdex.normalize import normalize_card, normalize_set

scenarios("features/rich_catalog.feature")


@given("a collected French Pokemon card with rules and illustrator", target_fixture="rich_client")
def rich_client(tmp_path):
    url = f"sqlite:///{tmp_path / 'rich.db'}"
    repository = Repository(url)
    metadata.create_all(repository.engine)
    raw = json.loads(Path("tests/fixtures/tcgdex_charizard.json").read_text())
    raw["pricing"] = {"cardmarket": {"avg": 100}}
    raw["variants_detailed"] = [{"name": "holo", "pricing": {"usd": 50}}]
    card = normalize_card(
        raw, language="fr", source_url="https://api.tcgdex.net/v2/fr/cards/base1-4"
    )
    repository.save(card.model_dump(mode="json") | {"images": []})
    repository.save_set(
        normalize_set(
            {
                "id": "base1",
                "name": "Set de Base",
                "serie": {"id": "base", "name": "Base"},
            },
            language="fr",
        )
    )
    with TestClient(create_app(url, tmp_path / "images", tmp_path / "jobs")) as client:
        yield client
    repository.close()


@when("I open its catalog detail", target_fixture="detail")
def detail(rich_client):
    response = rich_client.get(
        "/api/cards/detail",
        params={"game": "pokemon", "source": "tcgdex", "source_id": "base1-4", "language": "fr"},
    )
    assert response.status_code == 200
    return response.json()


@then("I read its localized set name, HP, attack cost and illustrator")
def information(detail):
    assert detail["set_name"] == "Set de Base"
    assert detail["illustrators"] == ["Mitsuhiro Arita"]
    assert detail["faces"][0]["statistics"]["hp"] == 120
    assert detail["faces"][0]["abilities"][1]["cost"]["symbols"] == ["Feu"] * 4


@then("the original source payload is still available")
def original(detail, rich_client):
    assert detail["raw"]["unmapped_future_field"] == {"anything": "preserved"}

    page = rich_client.get("/api/cards").json()
    assert page["items"][0]["set_name"] == "Set de Base"
    assert "raw" not in page["items"][0]
    assert "faces" not in page["items"][0]
    sets = rich_client.get("/api/overview").json()["sets"]
    assert sets[0]["names"]["fr"] == "Set de Base"
    assert rich_client.get("/api/sets").json()[0]["name"] == "Set de Base"


@then("monetary values are excluded but gameplay costs remain")
def no_prices(detail):
    assert "pricing" not in detail["raw"]
    assert "pricing" not in detail["game_data"]["pokemon"]
    assert detail["raw"]["variants_detailed"] == [{"name": "holo"}]
    assert detail["faces"][0]["costs"]["retreat"]["value"] == 3


@when("I browse the Base block", target_fixture="block_cards")
def browse_block(rich_client):
    return rich_client.get(
        "/api/cards",
        params={
            "game": "pokemon",
            "source": "tcgdex",
            "language": "fr",
            "block_id": "base",
        },
    ).json()


@then("I find the card through its extension and localized block")
def block_result(block_cards, rich_client):
    assert block_cards["total"] == 1
    assert block_cards["items"][0]["block_name"] == "Base"
    assert block_cards["items"][0]["set_name"] == "Set de Base"
    assert rich_client.get("/api/blocks").json()[0]["source_id"] == "base"
    assert rich_client.get("/api/cards", params={"block_id": "missing"}).json()["total"] == 0
