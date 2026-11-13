import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/collection.feature")


@when(
    "I request the complete TCGdex extension swsh12.5 in French and English",
    target_fixture="job",
)
def enqueue_scope(client):
    response = client.post(
        "/api/jobs",
        json={
            "kind": "collect_scope",
            "languages": ["fr", "en", "fr"],
            "scope": {"kind": "set", "id": "swsh12.5"},
        },
        headers={"X-TCG-Admin": "1"},
    )
    assert response.status_code == 202
    return response.json()


@then("the queued collection preserves the extension without a card limit")
def queued_scope(client, job):
    expected = {
        "kind": "collect_scope",
        "spider": "tcgdex",
        "languages": ["fr", "en"],
        "scope": {"kind": "set", "id": "swsh12.5"},
        "force": False,
    }
    assert job["status"] == "queued"
    assert job["parameters"] == expected
    assert client.get(f"/api/jobs/{job['id']}").json()["parameters"] == expected


@pytest.mark.parametrize(
    "extra",
    [
        {"limit": 10},
        {"card_ids": ["base1-1"]},
        {"scope": {"kind": "block", "id": "../base"}},
        {"scope": {"kind": "block", "id": "--settings=evil"}},
        {"scope": {"kind": "block", "id": ""}},
        {"scope": {"kind": "all", "id": "base"}},
        {"languages": ["xx"]},
    ],
)
def test_scoped_request_rejects_ambiguous_or_unsafe_parameters(client, extra):
    response = client.post(
        "/api/jobs",
        json={"kind": "collect_scope", "scope": {"kind": "block", "id": "base"}} | extra,
        headers={"X-TCG-Admin": "1"},
    )
    assert response.status_code == 422
    assert client.get("/api/jobs").json() == []


TCGDEX_LANGUAGES = [
    "en",
    "fr",
    "es",
    "es-mx",
    "it",
    "pt",
    "pt-br",
    "pt-pt",
    "de",
    "nl",
    "pl",
    "ru",
    "ja",
    "ko",
    "zh-tw",
    "id",
    "th",
    "zh-cn",
]


@when("I request a repair of missing images", target_fixture="job")
def enqueue_image_repair(client):
    response = client.post(
        "/api/jobs", json={"kind": "repair_images"}, headers={"X-TCG-Admin": "1"}
    )
    assert response.status_code == 202
    return response.json()


@then("an image repair appears in the persistent history")
def queued_image_repair(client, job):
    assert job["status"] == "queued"
    assert job["parameters"] == {"kind": "repair_images"}
    assert client.get(f"/api/jobs/{job['id']}").json()["parameters"] == job["parameters"]
    assert client.get("/api/jobs").json()[0]["parameters"] == job["parameters"]


def test_image_repair_does_not_accept_arbitrary_urls_or_collection_options(client):
    for extra in ({"url": "https://example.com"}, {"force": True}, {"limit": 1}):
        response = client.post(
            "/api/jobs",
            json={"kind": "repair_images"} | extra,
            headers={"X-TCG-Admin": "1"},
        )
        assert response.status_code == 422


@then("all eighteen TCGdex languages are available")
def available_languages(client):
    connector = next(item for item in client.get("/api/spiders").json() if item["id"] == "tcgdex")
    assert set(connector["languages"]) == set(TCGDEX_LANGUAGES)


@when("I request a TCGdex collection in all eighteen languages", target_fixture="job")
def enqueue_all_languages(client):
    response = client.post(
        "/api/jobs",
        json={"spider": "tcgdex", "languages": TCGDEX_LANGUAGES, "limit": 2},
        headers={"X-TCG-Admin": "1"},
    )
    assert response.status_code == 202
    return response.json()


@then("the queued collection preserves all eighteen language codes")
def queued_languages(client, job):
    assert job["status"] == "queued"
    assert job["parameters"]["languages"] == TCGDEX_LANGUAGES
    persisted = client.get(f"/api/jobs/{job['id']}").json()
    assert persisted["parameters"]["languages"] == TCGDEX_LANGUAGES
    assert client.get("/api/jobs").json()[0]["parameters"]["languages"] == TCGDEX_LANGUAGES


@given("an administrator viewing the local catalog")
def admin(client):
    assert client.get("/api/spiders").status_code == 200


@when("I request a TCGdex collection in French with a limit of two", target_fixture="job")
def enqueue(client):
    response = client.post(
        "/api/jobs",
        json={"spider": "tcgdex", "languages": ["fr"], "limit": 2},
        headers={"X-TCG-Admin": "1"},
    )
    assert response.status_code == 202
    return response.json()


@then("a queued collection appears in the persistent history")
def queued(client, job):
    assert job["status"] == "queued"
    assert client.get("/api/jobs").json()[0]["id"] == job["id"]
    assert client.get(f"/api/jobs/{job['id']}").json()["parameters"]["limit"] == 2


def test_admin_rejects_arbitrary_commands_and_unsafe_origins(client):
    headers = {"X-TCG-Admin": "1"}
    assert client.post("/api/jobs", json={"spider": "shell"}, headers=headers).status_code == 422
    assert client.post("/api/jobs", json={"limit": 0}, headers=headers).status_code == 422
    assert client.post("/api/jobs", json={"languages": ["xx"]}, headers=headers).status_code == 422
    assert (
        client.post(
            "/api/jobs", json={"card_ids": ["--settings=evil"]}, headers=headers
        ).status_code
        == 422
    )
    assert client.post("/api/jobs", json={}).status_code == 403
    assert (
        client.post(
            "/api/jobs", json={}, headers=headers | {"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    assert client.get("/api/jobs").json() == []


def test_unknown_job_and_invalid_page_are_not_silent_successes(client):
    assert client.get("/api/jobs/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/api/cards?page=0").status_code == 422
    assert client.get("/api/cards?page_size=500").status_code == 422
