from fastapi.testclient import TestClient
from tcg_api.app import create_app
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata


def test_readiness_requires_a_usable_catalog_database(tmp_path):
    url = f"sqlite:///{tmp_path / 'health.db'}"
    repository = Repository(url)
    with TestClient(create_app(url, tmp_path / "images", tmp_path / "jobs")) as client:
        response = client.get("/api/health")
        assert response.status_code == 503
        assert response.json() == {"detail": "Catalog database unavailable"}
        metadata.create_all(repository.engine)
        assert client.get("/api/health").json() == {"status": "ok"}
    repository.close()


def test_card_deep_links_and_collection_reload_serve_the_admin(tmp_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    shell = "<!doctype html><html><body>Atlas admin</body></html>"
    (frontend / "index.html").write_text(shell)
    app = create_app("sqlite://", tmp_path / "images", tmp_path / "jobs", frontend_dir=frontend)
    with TestClient(app) as client:
        for url in ["/", "/cards/pokemon/tcgdex/fr/base1-4", "/collections"]:
            response = client.get(url)
            assert response.status_code == 200
            assert response.text == shell
            assert response.headers["content-type"].startswith("text/html")
        for url in ["/api/unknown", "/assets/missing.js", "/api/images/missing.webp"]:
            assert client.get(url).status_code == 404
