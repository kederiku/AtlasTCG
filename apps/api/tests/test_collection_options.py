import http.server
import json
import threading
import time
import urllib.request
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from tcg_api.app import create_app
from tcg_api.discovery import TCGdexDiscovery


def test_invalid_discovery_parameters_are_rejected_without_contacting_a_source(tmp_path):
    with TestClient(create_app("sqlite://", tmp_path / "images", tmp_path / "jobs")) as client:
        for query in (
            "languages=xx",
            "languages=",
            "languages=fr&locale=xx",
            "languages=fr&block_id=../swsh",
        ):
            response = client.get("/api/collection-options/tcgdex/sets?" + query)
            assert response.status_code == 422


@pytest.fixture
def directory(tmp_path, monkeypatch):
    responses = {
        "/v2/en/series": [{"id": "swsh", "name": "Sword & Shield", "prices": {"usd": 5}}],
        "/v2/fr/series": [
            {"id": "swsh", "name": "Épée et Bouclier"},
            {"id": "only-fr", "name": "FR"},
        ],
        "/v2/es/series": [{"id": "swsh", "name": "Espada y Escudo"}],
        "/v2/en/sets": [
            {"id": "swsh12.5", "name": "Crown Zenith"},
            {"id": "orphan", "name": "Orphan"},
        ],
        "/v2/fr/sets": [{"id": "swsh12.5", "name": "Zénith Suprême"}],
        "/v2/en/series/swsh": {"id": "swsh", "sets": [{"id": "swsh12.5", "name": "Crown Zenith"}]},
    }
    visited = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            visited.append(self.path)
            value = responses.get(self.path, 404)
            if value == "slow":
                time.sleep(0.1)
                value = []
            if isinstance(value, int):
                self.send_response(value)
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
            try:
                self.wfile.write(value if isinstance(value, bytes) else json.dumps(value).encode())
            except BrokenPipeError:
                pass

        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original_open = urllib.request.OpenerDirector.open

    def local_open(opener, request, *args, **kwargs):
        # Intercept only the remote transport; all parsing and business rules run.
        url = request.full_url if isinstance(request, urllib.request.Request) else request
        assert urlsplit(url).hostname == "api.tcgdex.net"
        return original_open(
            opener, f"http://127.0.0.1:{server.server_port}{urlsplit(url).path}", *args, **kwargs
        )

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", local_open)
    discovery = TCGdexDiscovery(timeout=0.05)
    try:
        with TestClient(
            create_app("sqlite://", tmp_path / "images", tmp_path / "jobs", discovery=discovery)
        ) as client:
            yield client, responses, visited
    finally:
        discovery.close()
        server.shutdown()
        server.server_close()
        thread.join()


def test_choices_merge_codes_and_use_interface_names_without_widening_languages(directory):
    client, _responses, _visited = directory
    response = client.get("/api/collection-options/tcgdex/blocks?languages=en&locale=es")
    assert response.status_code == 200
    assert response.json() == [{"id": "swsh", "name": "Espada y Escudo", "languages": ["en"]}]
    response = client.get("/api/collection-options/tcgdex/blocks?languages=en,fr&locale=de")
    assert response.status_code == 422
    response = client.get("/api/collection-options/tcgdex/blocks?languages=en,fr&locale=fr")
    assert {item["id"]: item["languages"] for item in response.json()} == {
        "swsh": ["en", "fr"],
        "only-fr": ["fr"],
    }


def test_all_sets_include_unassigned_sets_and_block_choice_filters_using_source_membership(
    directory,
):
    client, _responses, _visited = directory
    response = client.get("/api/collection-options/tcgdex/sets?languages=en&locale=fr")
    assert response.status_code == 200
    assert {item["id"]: item["name"] for item in response.json()} == {
        "swsh12.5": "Zénith Suprême",
        "orphan": "Orphan",
    }
    response = client.get(
        "/api/collection-options/tcgdex/sets?languages=fr,en&locale=fr&block_id=swsh"
    )
    assert response.json() == [{"id": "swsh12.5", "name": "Crown Zenith", "languages": ["en"]}]


@pytest.mark.parametrize(
    "value",
    [
        503,
        302,
        "slow",
        b"invalid",
        {"wrong": []},
        [{"id": "../oops", "name": "Invalid"}],
        [{"id": "swsh", "name": False}],
        b" " * (2 * 1024 * 1024 + 1),
    ],
)
def test_source_failure_never_becomes_a_partial_list(directory, value):
    client, responses, _visited = directory
    responses["/v2/fr/series"] = value
    response = client.get("/api/collection-options/tcgdex/blocks?languages=fr,en")
    assert response.status_code == 503


def test_absent_localized_scope_is_an_empty_list_but_wrong_identity_is_an_error(directory):
    client, responses, _visited = directory
    url = "/api/collection-options/tcgdex/sets?languages=fr&block_id=unknown"
    assert client.get(url).json() == []
    responses["/v2/fr/series/unknown"] = {"id": "other", "sets": []}
    assert client.get(url).status_code == 503
