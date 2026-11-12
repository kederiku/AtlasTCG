from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from tcg_api.app import create_app
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata


def test_api_without_frontend_exposes_queued_jobs_and_bounded_logs(tmp_path):
    url = f"sqlite:///{tmp_path / 'catalog.db'}"
    repository = Repository(url)
    metadata.create_all(repository.engine)
    try:
        with TestClient(
            create_app(
                url, tmp_path / "images", tmp_path / "jobs", frontend_dir=tmp_path / "missing"
            )
        ) as client:
            assert client.get("/api/health").status_code == 200
            assert client.get("/").status_code == 404
            response = client.post("/api/jobs", json={}, headers={"X-TCG-Admin": "1"})
            assert response.status_code == 202
            job = response.json()
            assert job["status"] == "queued"
            assert job["started_at"] is None
            assert job["finished_at"] is None
            persisted = client.get(f"/api/jobs/{job['id']}").json()
            assert {k: v for k, v in persisted.items() if k != "created_at"} == {
                k: v for k, v in job.items() if k != "created_at"
            }
            assert datetime.fromisoformat(persisted["created_at"]).replace(
                tzinfo=UTC
            ) == datetime.fromisoformat(job["created_at"])
            assert client.get("/api/jobs").json() == [persisted]
            log_url = f"/api/jobs/{job['id']}/logs"
            assert client.get(log_url).text == "En attente du worker…"
            path = tmp_path / "jobs" / job["id"] / "crawl.log"
            path.parent.mkdir(parents=True)
            body = ("été" * 20000).encode()
            path.write_bytes(body)
            assert client.get(log_url).text == body[-64000:].decode("utf-8", errors="replace")
            assert client.get(f"/api/jobs/{uuid4()}/logs").status_code == 404
            assert client.get("/api/jobs/not-a-uuid/logs").status_code == 422
    finally:
        repository.close()


def test_collection_responses_publish_explicit_openapi_contracts(tmp_path):
    with TestClient(create_app("sqlite://", tmp_path / "images", tmp_path / "jobs")) as client:
        schema = client.get("/openapi.json").json()
    response = schema["paths"]["/api/jobs"]["post"]["responses"]["202"]
    assert "$ref" in response["content"]["application/json"]["schema"]
