"""Repair existing observations against a local source, never real TCGdex."""

import http.server
import json
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image
from sqlalchemy import select
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import cards, metadata
from tcg_scraping.runner import collection_result


@pytest.fixture
def world(tmp_path):
    requests = []
    responses = {}
    first_downloads = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            if self.path == "/slow.png":
                if requests.count("/slow.png") >= 2:
                    first_downloads.set()
                first_downloads.wait(timeout=5)
                # Deliberate source latency lets the crawler fill its work queue.
                if requests.count("/slow.png") <= 2:
                    time.sleep(0.2)
            value = responses.get(self.path, 404)
            self.send_response(value if isinstance(value, int) else 200)
            self.end_headers()
            if not isinstance(value, int):
                self.wfile.write(json.dumps(value).encode() if isinstance(value, dict) else value)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    database_url = f"sqlite:///{tmp_path / 'catalog.db'}"
    repository = Repository(database_url)
    metadata.create_all(repository.engine)
    images = tmp_path / "images"
    images.mkdir()
    script = tmp_path / "repair.py"
    script.write_text("""
import os
from urllib.parse import quote
from scrapy.crawler import CrawlerProcess
from scrapy import signals
from scrapy.spiderloader import SpiderLoader
from scrapy.utils.project import get_project_settings
settings = get_project_settings()
settings.set("ADMIN_STATS_PATH", os.environ["FIXTURE_STATS_PATH"])
settings.set("DOWNLOAD_DELAY", 0)
settings.set("AUTOTHROTTLE_ENABLED", False)
settings.set("RETRY_TIMES", 0)
settings.set("FILES_EXPIRES", 0)
spider = SpiderLoader.from_settings(settings).load("repair_images")
class FixtureRepair(spider):
    def discovery_url(self, candidate):
        return (os.environ["FIXTURE_URL"] + "/v2/" + candidate.language
                + "/cards/" + quote(candidate.source_id, safe=""))
process = CrawlerProcess(settings)
crawler = process.create_crawler(FixtureRepair)
def first_media(response):
    if (response.url.endswith("/slow.png")
            and crawler.stats.get_value("test/first_media_examined") is None):
        crawler.stats.set_value(
            "test/first_media_examined", crawler.stats.get_value("images/examined"))
crawler.signals.connect(first_media, signal=signals.response_downloaded)
process.crawl(crawler)
process.start()
""")

    def run():
        stats_path = tmp_path / "stats.json"
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            env=os.environ
            | {
                "SCRAPY_SETTINGS_MODULE": "tcg_scraping.settings",
                "TCG_DATABASE_URL": database_url,
                "TCG_IMAGES_DIR": str(images),
                "FIXTURE_URL": base,
                "FIXTURE_STATS_PATH": str(stats_path),
            },
        )
        assert result.returncode == 0, result.stderr
        assert stats_path.exists(), result.stderr
        stats = json.loads(stats_path.read_text())
        return collection_result(result.returncode, stats), result.stderr

    output = BytesIO()
    Image.new("RGB", (12, 18), "green").save(output, format="PNG")
    try:
        yield SimpleNamespace(
            repo=repository,
            images=images,
            base=base,
            responses=responses,
            requests=requests,
            run=run,
            png=output.getvalue(),
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        repository.close()


def save(world, language="fr", **changes):
    world.repo.save(
        {
            "game": "pokemon",
            "source": "tcgdex",
            "source_id": "base1-4",
            "language": language,
            "name": "Observation originale",
            "set_id": "base1",
            "number": "4",
            "source_url": "https://api.tcgdex.net/previous",
            "image_urls": [],
            "images": [],
            "raw": {"name": "Observation originale"},
            "updated_at": datetime(2024, 1, 2, tzinfo=UTC),
        }
        | changes,
        preserve_updated_at=True,
    )


def observations(world):
    with world.repo.engine.connect() as connection:
        return {row["language"]: dict(row) for row in connection.execute(select(cards)).mappings()}


def test_repair_downloads_known_and_discovered_images_and_can_be_repeated(world):
    world.responses.update(
        {
            "/known.png": world.png,
            "/v2/es/cards/base1-4": {
                "id": "base1-4",
                "image": world.base + "/discovered",
                "pricing": {"usd": 99},
            },
            "/discovered/high.webp": world.png,
        }
    )
    save(world, "fr", image_urls=[world.base + "/known.png"])
    save(world, "es")
    save(world, "de")
    originals = {}
    for language in ("en", "it"):
        path = f"pokemon/{language}/base1/4-base1.webp"
        destination = world.images / path
        destination.parent.mkdir(parents=True)
        Image.new("RGB", (12, 18), "red").save(destination, format="WEBP", lossless=True)
        os.utime(destination, (0, 0))
        originals[path] = destination.read_bytes()
        save(
            world,
            language,
            images=[{"path": path, "checksum": "original"}] if language == "en" else [],
        )
    before = observations(world)
    result, log = world.run()
    assert result.status == "succeeded", log
    assert {
        key: result.stats.get("images/" + key, 0)
        for key in ("examined", "downloaded", "present", "unavailable", "errors")
    } == {
        "examined": 5,
        "downloaded": 2,
        "present": 2,
        "unavailable": 1,
        "errors": 0,
    }
    assert sorted(world.requests) == [
        "/discovered/high.webp",
        "/known.png",
        "/v2/de/cards/base1-4",
        "/v2/es/cards/base1-4",
    ]
    after = observations(world)
    for language in before:
        assert {k: v for k, v in after[language].items() if k not in {"image_urls", "images"}} == {
            k: v for k, v in before[language].items() if k not in {"image_urls", "images"}
        }
    assert after["es"]["image_urls"] == [world.base + "/discovered/high.webp"]
    for language in ("fr", "es"):
        with Image.open(world.images / after[language]["images"][0]["path"]) as image:
            assert image.format == "WEBP"
            assert image.convert("RGB").getpixel((0, 0)) == (0, 128, 0)
    assert {path: (world.images / path).read_bytes() for path in originals} == originals
    assert after["en"] == before["en"]
    assert after["it"]["images"] == [{"path": "pokemon/it/base1/4-base1.webp"}]
    world.requests.clear()
    result, log = world.run()
    assert result.status == "succeeded", log
    assert result.stats.get("images/downloaded", 0) == 0
    assert result.stats["images/present"] == 4
    assert world.requests == ["/v2/de/cards/base1-4"]


@pytest.mark.parametrize(
    "response",
    [
        {"id": "different-card", "image": "/wrong"},
        b"not json",
        {"id": "base1-4", "image": 12},
        {"id": "base1-4", "image": []},
        {"id": "base1-4", "image": {}},
        {"id": "base1-4", "image": False},
        {"id": "base1-4", "image": 0},
        503,
    ],
)
def test_invalid_discovery_is_reported_and_other_printings_are_repaired(world, response):
    if isinstance(response, dict) and isinstance(response.get("image"), str):
        response = response | {"image": world.base + response["image"]}
    world.responses.update(
        {"/v2/fr/cards/base1-4": response, "/wrong/high.webp": world.png, "/valid.png": world.png}
    )
    save(world)
    save(world, "en", image_urls=[world.base + "/valid.png"])
    before = observations(world)["fr"]
    result, log = world.run()
    assert result.status == "failed", log
    assert result.stats["images/errors"] == 1
    assert result.stats["images/downloaded"] == 1
    assert observations(world)["fr"] == before
    assert observations(world)["en"]["images"]


@pytest.mark.parametrize("escape", ["../outside.webp", "link/outside.webp"])
def test_image_paths_cannot_escape_the_configured_storage(tmp_path, escape):
    from tcg_scraping.image_repair import LocalImagePresence

    root = tmp_path / "images"
    root.mkdir()
    (root / "link").symlink_to(tmp_path, target_is_directory=True)
    (tmp_path / "outside.webp").write_bytes(b"untouched")
    with pytest.raises(ValueError, match="storage"):
        LocalImagePresence(root).exists(escape)


def test_multiface_failure_keeps_existing_files_and_retains_discovered_url_for_retry(world):
    path = "pokemon/fr/base1/4-base1.webp"
    existing = world.images / path
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"existing file must remain unchanged")
    world.responses.update(
        {
            "/second.png": world.png,
            "/third.png": b"not an image",
            "/v2/es/cards/base1-4": {"id": "base1-4", "image": world.base + "/missing"},
        }
    )
    save(
        world,
        image_urls=[
            world.base + "/first.png",
            world.base + "/second.png",
            world.base + "/third.png",
        ],
        images=[{"path": path}],
    )
    save(world, "es")
    before = observations(world)
    result, log = world.run()
    assert result.status == "failed", log
    assert result.stats["images/errors"] == 2
    assert observations(world)["fr"] == before["fr"]
    assert observations(world)["es"]["image_urls"] == [world.base + "/missing/high.webp"]
    assert observations(world)["es"]["images"] == []
    assert existing.read_bytes() == b"existing file must remain unchanged"
    assert list(world.images.rglob("*.webp")) == [existing]
    assert "/first.png" not in world.requests


def test_large_repair_limits_in_flight_work_while_images_are_slow(world):
    world.responses["/slow.png"] = world.png
    for number in range(50):
        save(
            world,
            source_id=f"base1-{number}",
            number=str(number),
            image_urls=[world.base + "/slow.png"],
        )
    result, log = world.run()
    assert result.stats["test/first_media_examined"] <= 8
    assert result.status == "succeeded", log
    assert result.stats["images/examined"] == 50
    assert result.stats["images/downloaded"] == 50
    assert len(list(world.images.rglob("*.webp"))) == 50
