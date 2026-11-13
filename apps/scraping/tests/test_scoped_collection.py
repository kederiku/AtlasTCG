"""Collect the chosen source perimeter through a real local HTTP server."""

import http.server
import json
import os
import subprocess
import sys
import threading

import pytest
from tcg_core.collections.models import job_request_adapter
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata
from tcg_scraping.runner import ScrapyCollector, collection_result


@pytest.fixture
def source(tmp_path):
    documents = {}
    visited = []
    for language in ("fr", "en"):
        prefix = f"/v2/{language}"
        documents[f"{prefix}/cards"] = []
        documents[f"{prefix}/series/swsh"] = {
            "id": "swsh",
            "name": "Bloc",
            "sets": [{"id": "swsh12.5"}, {"id": "swsh3"}],
        }
        for set_id, count in (("swsh12.5", 11), ("swsh3", 1)):
            documents[f"{prefix}/sets/{set_id}"] = {
                "id": set_id,
                "name": set_id,
                "serie": {"id": "swsh", "name": "Bloc"},
                "cards": [{"id": f"{set_id}-{n}"} for n in range(1, count + 1)],
            }
            for n in range(1, count + 1):
                documents[f"{prefix}/cards/{set_id}-{n}"] = {
                    "id": f"{set_id}-{n}",
                    "name": f"Carte {n}",
                    "localId": str(n),
                    "set": {"id": set_id, "name": set_id},
                }

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            visited.append(self.path)
            self.send_response(200 if self.path in documents else 404)
            self.end_headers()
            self.wfile.write(json.dumps(documents.get(self.path, {})).encode())

        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"sqlite:///{tmp_path / 'catalog.db'}"
    repository = Repository(url)
    metadata.create_all(repository.engine)
    script = tmp_path / "crawl_scope.py"
    script.write_text("""
import json, os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from tcg_scraping.sources.tcgdex.spider import TCGdexSpider
class LocalSpider(TCGdexSpider):
    allowed_domains = ["127.0.0.1"]
    api_url = os.environ["FIXTURE_URL"] + "/v2"
    def endpoint(self, language, card_id=""):
        return self.api_url + "/" + language + "/cards" + ("/" + card_id if card_id else "")
settings = get_project_settings()
settings.setdict({"DOWNLOAD_DELAY": 0, "AUTOTHROTTLE_ENABLED": False,
                  "RETRY_TIMES": 0, "ADMIN_STATS_PATH": os.environ["STATS_PATH"]})
process = CrawlerProcess(settings)
process.crawl(LocalSpider, **json.loads(os.environ["CRAWL_ARGUMENTS"]))
process.start()
""")

    def crawl(**arguments):
        visited.clear()
        stats_path = tmp_path / "stats.json"
        stats_path.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, str(script)],
            env=os.environ
            | {
                "FIXTURE_URL": f"http://127.0.0.1:{server.server_port}",
                "SCRAPY_SETTINGS_MODULE": "tcg_scraping.settings",
                "TCG_DATABASE_URL": url,
                "TCG_IMAGES_DIR": str(tmp_path / "images"),
                "CRAWL_ARGUMENTS": json.dumps(arguments),
                "STATS_PATH": str(stats_path),
            },
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        stats = json.loads(stats_path.read_text())
        return collection_result(result.returncode, stats)

    try:
        yield documents, visited, repository, crawl
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        repository.close()


@pytest.mark.parametrize(("argument", "expected_count"), [("block_id", 12), ("set_id", 11)])
def test_collects_every_card_only_within_the_requested_perimeter(source, argument, expected_count):
    _documents, visited, repository, crawl = source
    result = crawl(languages="fr", **{argument: "swsh" if argument == "block_id" else "swsh12.5"})
    assert result.status == "succeeded", result.stats
    assert repository.search()["total"] == expected_count
    assert "/v2/fr/cards" not in visited
    if argument == "set_id":
        assert "/v2/fr/sets/swsh3" not in visited
    assert visited.count("/v2/fr/series/swsh") == 1
    assert visited.count("/v2/fr/sets/swsh12.5") == 1


def test_scoped_runner_keeps_perimeter_and_refresh_without_a_limit(tmp_path):
    request = job_request_adapter.validate_python(
        {
            "kind": "collect_scope",
            "languages": ["fr", "en"],
            "scope": {"kind": "set", "id": "swsh12.5"},
            "force": True,
        }
    )
    command = ScrapyCollector(tmp_path).command("scope", request)
    assert command[4] == "tcgdex"
    assert "set_id=swsh12.5" in command
    assert "languages=fr,en" in command
    assert "force=true" in command
    assert not any(part.startswith(("limit=", "card_ids=")) for part in command)


def test_scope_missing_in_one_language_is_reported_while_other_language_is_collected(source):
    documents, _visited, repository, crawl = source
    del documents["/v2/fr/sets/swsh12.5"]
    result = crawl(languages="fr,en", set_id="swsh12.5")
    assert result.status == "succeeded", result.stats
    assert result.stats["scope/languages_unavailable"] == 1
    assert result.stats["scope/languages_found"] == 1
    assert repository.search(language="fr")["total"] == 0
    assert repository.search(language="en")["total"] == 11


def test_scope_missing_in_every_requested_language_fails(source):
    documents, _visited, repository, crawl = source
    del documents["/v2/fr/sets/swsh12.5"]
    result = crawl(languages="fr", set_id="swsh12.5")
    assert result.status == "failed"
    assert result.stats["scope/languages_unavailable"] == 1
    assert repository.search()["total"] == 0


@pytest.mark.parametrize(
    "broken",
    ["missing_set", "missing_card", "wrong_set", "wrong_card", "foreign_card", "invalid_list"],
)
def test_announced_resources_must_exist_and_match_the_perimeter(source, broken):
    documents, _visited, _repository, crawl = source
    if broken == "missing_set":
        del documents["/v2/fr/sets/swsh3"]
    elif broken == "missing_card":
        del documents["/v2/fr/cards/swsh3-1"]
    elif broken == "wrong_set":
        documents["/v2/fr/sets/swsh3"]["id"] = "other"
    elif broken == "wrong_card":
        documents["/v2/fr/cards/swsh3-1"]["id"] = "other-1"
    elif broken == "foreign_card":
        documents["/v2/fr/cards/swsh3-1"]["set"]["id"] = "other"
    else:
        documents["/v2/fr/sets/swsh3"]["cards"] = {}
    result = crawl(languages="fr", block_id="swsh")
    assert result.status == "failed", result.stats


def test_empty_scope_is_distinct_from_an_unavailable_scope(source):
    documents, _visited, repository, crawl = source
    documents["/v2/fr/sets/swsh12.5"]["cards"] = []
    result = crawl(languages="fr", set_id="swsh12.5")
    assert result.status == "succeeded", result.stats
    assert result.stats["scope/languages_found"] == 1
    assert repository.search()["total"] == 0


def test_scoped_collection_preserves_existing_filter_and_explicit_refresh(source):
    documents, visited, repository, crawl = source
    assert crawl(languages="fr", set_id="swsh3").status == "succeeded"
    documents["/v2/fr/cards/swsh3-1"]["name"] = "Actualisée"
    result = crawl(languages="fr", set_id="swsh3")
    assert result.status == "succeeded", result.stats
    assert result.stats["cards/skipped_existing"] == 1
    assert "/v2/fr/cards/swsh3-1" not in visited
    assert repository.search()["items"][0]["name"] == "Carte 1"
    assert crawl(languages="fr", set_id="swsh3", force="true").status == "succeeded"
    assert repository.search()["items"][0]["name"] == "Actualisée"


def test_partially_collected_block_succeeds_and_only_adds_missing_cards(source):
    _documents, _visited, repository, crawl = source
    assert crawl(languages="fr", set_id="swsh3").status == "succeeded"
    result = crawl(languages="fr", block_id="swsh")
    assert result.status == "succeeded", result.stats
    assert result.stats["cards/skipped_existing"] == 1
    assert result.stats["cards/stored"] == 11
    assert repository.search()["total"] == 12
