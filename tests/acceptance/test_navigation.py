from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when
from tcg_api.app import create_app
from tcg_core.catalog.models import Card
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata

scenarios("features/navigation.feature")


@given("an extension and a card collected in French and Spanish", target_fixture="navigation")
def navigation(tmp_path):
    url = f"sqlite:///{tmp_path / 'navigation.db'}"
    repository = Repository(url)
    metadata.create_all(repository.engine)
    for language, name, extension, block in [
        ("fr", "Carte française", "Destinées Futures", "Noir et Blanc"),
        ("es", "Carta española", "Destinos Futuros", "Negro y Blanco"),
    ]:
        repository.save(
            Card(
                game="pokemon",
                source="tcgdex",
                source_id="bw4-1",
                language=language,
                name=name,
                set_id="bw4",
                number="1",
                source_url="https://example.com/card",
                set_info={"name": extension, "block": {"id": "bw", "name": block}},
            ).model_dump(mode="json")
        )
    with TestClient(create_app(url, tmp_path / "images", tmp_path / "jobs")) as client:
        yield client
    repository.close()


@when("I find Spanish extension names with French cards", target_fixture="result")
def find_translated_extension(navigation):
    response = navigation.get(
        "/api/card-groups",
        params={
            "q": "Destinos Futuros",
            "language": "fr",
            "display_language": "fr",
        },
    )
    assert response.status_code == 200
    return response.json()


@then("I see one French card with links to both collected languages")
def french_group(result):
    assert result["total"] == 1
    assert result["items"][0]["language"] == "fr"
    assert {v["language"] for v in result["items"][0]["versions"]} == {"fr", "es"}


@when("I browse the Spanish cards with a French interface", target_fixture="result")
def spanish_cards(navigation):
    response = navigation.get(
        "/api/card-groups",
        params={
            "block_id": "bw",
            "set_id": "bw4",
            "language": "es",
            "display_language": "fr",
        },
    )
    assert response.status_code == 200
    return response.json()


@then("the representative card is Spanish and its other language remains available")
def spanish_group(result, navigation):
    assert result["total"] == 1
    card = result["items"][0]
    assert card["name"] == "Carta española"
    assert card["language"] == "es"
    assert {v["language"] for v in card["versions"]} == {"fr", "es"}
    detail = navigation.get(
        "/api/cards/detail",
        params={
            "game": "pokemon",
            "source": "tcgdex",
            "source_id": "bw4-1",
            "language": "es",
        },
    ).json()
    assert {v["language"] for v in detail["versions"]} == {"fr", "es"}
    assert navigation.get("/api/cards").json()["total"] == 2
