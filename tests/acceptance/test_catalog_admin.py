from pytest_bdd import given, scenarios, then, when

scenarios("features/catalog.feature")


@given("a catalog containing a French card and an English card")
def catalog(client):
    assert client.get("/api/cards").json()["total"] == 2


@when("I search for French cards named Dracaufeu", target_fixture="result")
def search(client):
    response = client.get("/api/cards", params={"language": "fr", "q": "Dracaufeu"})
    assert response.status_code == 200
    return response.json()


@then("I see only the French card with its local image")
def localized_card(client, result):
    assert result["total"] == 1
    card = result["items"][0]
    assert card["language"] == "fr"
    assert card["name"] == "Dracaufeu"
    assert client.get(card["image_urls"][0]).content == b"image"
