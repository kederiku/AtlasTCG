import pytest
from fastapi.testclient import TestClient
from tcg_api.app import create_app
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata


@pytest.fixture
def client(tmp_path):
    url = f"sqlite:///{tmp_path / 'catalog.db'}"
    repository = Repository(url)
    metadata.create_all(repository.engine)
    for lang, name in [("fr", "Dracaufeu"), ("en", "Charizard")]:
        path = f"pokemon/{lang}/base1/4-base1.webp"
        image = tmp_path / "images" / path
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"image")
        repository.save(
            dict(
                game="pokemon",
                source="tcgdex",
                source_id="base1-4",
                language=lang,
                name=name,
                set_id="base1",
                number="4",
                source_url="https://example.com/card",
                image_urls=[],
                images=[{"path": path}],
                raw={"rarity": "Rare"},
            )
        )
    with TestClient(create_app(url, tmp_path / "images", tmp_path / "jobs")) as client:
        yield client
    repository.close()
