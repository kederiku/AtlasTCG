from copy import deepcopy
from types import MappingProxyType, SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from tcg_api.app import create_app
from tcg_api.presentation.catalog import present_card, present_page
from tcg_core.catalog.models import Card
from tcg_core.catalog.queries import CatalogService
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata


@pytest.fixture
def catalog(tmp_path):
    url = f"sqlite:///{tmp_path / 'catalog.db'}"
    repository = Repository(url)
    metadata.create_all(repository.engine)
    card = Card(
        game="pokemon",
        source="tcgdex",
        source_id="base1-4",
        language="fr",
        name="Dracaufeu",
        set_id="base1",
        number="004",
        source_url="https://example.com/cards/base1-4",
        image_urls=["https://example.com/front.png", "https://example.com/back.png"],
    ).model_dump(mode="json")
    try:
        yield repository, url, card
    finally:
        repository.close()


@pytest.mark.parametrize(
    ("paths", "expected_urls"),
    [
        ([], []),
        (
            ["pokemon/fr/base1/004 été#?%.webp", "pokemon/fr/base1/004-verso.webp"],
            [
                "/api/images/pokemon/fr/base1/004%20%C3%A9t%C3%A9%23%3F%25.webp",
                "/api/images/pokemon/fr/base1/004-verso.webp",
            ],
        ),
    ],
)
def test_http_catalog_presents_local_media_and_preserves_source_urls(
    catalog, tmp_path, paths, expected_urls
):
    repository, url, card = catalog
    repository.save(card | {"images": [{"path": path} for path in paths]})
    images = tmp_path / "images"
    for index, relative_path in enumerate(paths):
        path = images / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"image-{index}".encode())

    with TestClient(create_app(url, images, tmp_path / "jobs")) as client:
        response = client.get("/api/cards", params={"language": "fr", "q": "Dracaufeu"})
        assert response.status_code == 200
        page = response.json()
        assert (page["total"], page["page"], page["page_size"]) == (1, 1, 24)
        summary = page["items"][0]
        assert summary["image_urls"] == expected_urls
        assert not {"source_image_urls", "raw", "faces", "game_data", "images"} & summary.keys()

        response = client.get(
            "/api/cards/detail",
            params={
                "game": "pokemon",
                "source": "tcgdex",
                "source_id": "base1-4",
                "language": "fr",
            },
        )
        assert response.status_code == 200
        detail = response.json()
        assert detail["image_urls"] == expected_urls
        assert detail["source_image_urls"] == [
            "https://example.com/front.png",
            "https://example.com/back.png",
        ]
        assert detail["number"] == "004"
        for index, image_url in enumerate(detail["image_urls"]):
            image = client.get(image_url)
            assert image.status_code == 200
            assert image.content == f"image-{index}".encode()


def test_http_catalog_returns_not_found_for_an_unknown_localized_identity(catalog, tmp_path):
    repository, url, card = catalog
    repository.save(card)
    with TestClient(create_app(url, tmp_path / "images", tmp_path / "jobs")) as client:
        response = client.get(
            "/api/cards/detail",
            params={
                "game": "pokemon",
                "source": "tcgdex",
                "source_id": "base1-4",
                "language": "en",
            },
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Card not found"}


@pytest.mark.parametrize("operation", ["search", "detail"])
def test_catalog_use_cases_preserve_reusable_observations(catalog, operation):
    repository, _, card = catalog
    repository.save(card | {"images": [{"path": "pokemon/fr/base1/004.webp"}]})
    page = repository.search()
    page["items"] = [dict(item) for item in page["items"]]
    identity = {key: card[key] for key in ("game", "source", "source_id", "language")}
    observation = repository.get(**identity)
    before_page, before_observation = deepcopy(page), deepcopy(observation)
    reader = SimpleNamespace(search=lambda **filters: page, get=lambda **key: observation)
    service = CatalogService(reader)

    for _ in range(2):
        result = (
            service.search()["items"][0] if operation == "search" else service.detail(**identity)
        )
        assert result["image_urls"] == [
            "https://example.com/front.png",
            "https://example.com/back.png",
        ]
        assert result["images"] == [{"path": "pokemon/fr/base1/004.webp"}]
        assert page == before_page
        assert observation == before_observation


def test_http_presentation_accepts_reusable_read_only_documents(catalog):
    _, _, card = catalog
    card["images"] = [{"path": "pokemon/fr/base1/004.webp"}]
    before = deepcopy(card)
    observation = MappingProxyType(card)
    page = MappingProxyType({"items": [observation], "total": 1, "page": 2, "page_size": 1})

    for _ in range(2):
        detail = present_card(observation)
        result = present_page(page)
        assert result["items"] == [detail]
        assert (result["total"], result["page"], result["page_size"]) == (1, 2, 1)
        assert detail["image_urls"] == ["/api/images/pokemon/fr/base1/004.webp"]
        assert detail["source_image_urls"] == [
            "https://example.com/front.png",
            "https://example.com/back.png",
        ]
        assert dict(observation) == before
        assert page["items"] == [before]
