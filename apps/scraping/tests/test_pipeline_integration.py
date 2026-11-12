"""Exercise real downloader, media pipeline and database without an external API."""

import functools
import http.server
import json
import os
import subprocess
import sys
import threading
from datetime import UTC, datetime

import pytest
from PIL import Image
from sqlalchemy import create_engine, select
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import cards, metadata
from tcg_scraping.runner import collection_result


def test_crawl_to_webp_and_database(tmp_path):
    Image.new("RGB", (20, 30), "red").save(tmp_path / "card.png")
    (tmp_path / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path)),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    database_url = f"sqlite:///{tmp_path / 'catalog.db'}"
    engine = create_engine(database_url)
    metadata.create_all(engine)
    script = tmp_path / "crawl.py"
    script.write_text("""
import os
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from tcg_scraping.sources.tcgdex.spider import TCGdexSpider
class FixtureSpider(TCGdexSpider):
    allowed_domains = ["127.0.0.1"]
    name = "fixture"
    async def start(self):
        yield scrapy.Request(os.environ["FIXTURE_URL"], callback=self.parse)
    def parse(self, response):
        for language in ("fr", "en"):
            yield dict(kind="block", game="test", source="fixture", source_id="cycle",
                       language=language, info={"name": "Cycle " + language}, is_complete=True)
            yield dict(kind="set", game="test", source="fixture", source_id="set",
                       language=language, info={"name": "Set", "block": {"id": "cycle"}},
                       is_complete=True)
            yield dict(game="test", source="fixture", source_id="1", language=language,
                   name="Carte", set_id="set", number="1", source_url=response.url,
                   image_urls=[response.url + "card.png"], raw={})
process = CrawlerProcess(get_project_settings())
process.crawl(FixtureSpider)
process.start()
""")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            env=os.environ
            | {
                "FIXTURE_URL": url + "/",
                "SCRAPY_SETTINGS_MODULE": "tcg_scraping.settings",
                "TCG_DATABASE_URL": database_url,
                "TCG_IMAGES_DIR": str(tmp_path / "images"),
            },
            capture_output=True,
            text=True,
            timeout=45,
        )
        assert result.returncode == 0, result.stderr
        with engine.connect() as connection:
            rows = connection.execute(select(cards)).mappings().all()
        assert len(rows) == 2, result.stderr
        repository = Repository(database_url)
        assert len(repository.list_blocks()) == 2, result.stderr
        assert all(row["block_id"] == "cycle" for row in repository.search()["items"])
        repository.close()
        assert {row["images"][0]["path"] for row in rows} == {
            "test/fr/set/1-set.webp",
            "test/en/set/1-set.webp",
        }
        assert all((tmp_path / "images" / row["images"][0]["path"]).is_file() for row in rows)
        with Image.open(tmp_path / "images" / rows[0]["images"][0]["path"]) as image:
            assert image.format == "WEBP"
            assert image.size == (20, 30)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        engine.dispose()


@pytest.mark.parametrize(
    ("second_image", "expires", "stale_back", "expected_status"),
    [
        ("corrupt.png", 0, False, "failed"),
        ("missing.png", 0, False, "failed"),
        ("replacement-back.png", 0, False, "succeeded"),
        ("corrupt.png", 30, False, "succeeded"),
        ("replacement-back.png", 30, True, "succeeded"),
    ],
)
def test_multiface_recollection_publishes_only_complete_media(
    tmp_path, second_image, expires, stale_back, expected_status
):
    Image.new("RGB", (20, 30), "green").save(tmp_path / "replacement.png")
    Image.new("RGB", (20, 30), "yellow").save(tmp_path / "replacement-back.png")
    (tmp_path / "corrupt.png").write_bytes(b"not an image")
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path)),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    database_url = f"sqlite:///{tmp_path / 'catalog.db'}"
    repository = Repository(database_url)
    metadata.create_all(repository.engine)
    image_paths = ["test/fr/set/1-set.webp", "test/fr/set/1-set-image-2.webp"]
    previous_files = {}
    for path, color in zip(image_paths, ["red", "blue"], strict=True):
        destination = tmp_path / "images" / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (20, 30), color).save(destination, format="WEBP", lossless=True)
        previous_files[path] = destination.read_bytes()
    if stale_back:
        os.utime(tmp_path / "images" / image_paths[1], (0, 0))
    repository.save(
        {
            "game": "test",
            "source": "fixture",
            "source_id": "1",
            "language": "fr",
            "name": "Observation précédente",
            "set_id": "set",
            "number": "1",
            "source_url": url + "/previous",
            "image_urls": [url + "/previous-front.png", url + "/previous-back.png"],
            "images": [{"path": path} for path in image_paths],
            "raw": {"observation": "previous"},
            "updated_at": datetime(2024, 1, 2, 3, 4, tzinfo=UTC),
        },
        preserve_updated_at=True,
    )
    with repository.engine.connect() as connection:
        previous_observation = dict(connection.execute(select(cards)).mappings().one())
    script = tmp_path / "recollect.py"
    script.write_text("""
import os
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from tcg_scraping.sources.tcgdex.spider import TCGdexSpider
class FixtureSpider(TCGdexSpider):
    allowed_domains = ["127.0.0.1"]
    name = "fixture"
    async def start(self):
        yield scrapy.Request(os.environ["FIXTURE_URL"], callback=self.parse)
    def parse(self, response):
        yield dict(game="test", source="fixture", source_id="1", language="fr",
                   name="Nouvelle observation", set_id="set", number="1",
                   source_url=response.url, raw={"observation": "replacement"},
                   image_urls=[response.url + "replacement.png",
                               response.url + os.environ["SECOND_IMAGE"]])
settings = get_project_settings()
# An explicit media refresh is required independently from observation refresh.
settings.set("FILES_EXPIRES", int(os.environ["FILES_EXPIRES"]))
settings.set("DOWNLOAD_DELAY", 0)
settings.set("AUTOTHROTTLE_ENABLED", False)
settings.set("ADMIN_STATS_PATH", os.environ["FIXTURE_STATS_PATH"])
process = CrawlerProcess(settings)
process.crawl(FixtureSpider)
process.start()
""")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            env=os.environ
            | {
                "FIXTURE_URL": url + "/",
                "SECOND_IMAGE": second_image,
                "FILES_EXPIRES": str(expires),
                "SCRAPY_SETTINGS_MODULE": "tcg_scraping.settings",
                "TCG_DATABASE_URL": database_url,
                "TCG_IMAGES_DIR": str(tmp_path / "images"),
                "FIXTURE_STATS_PATH": str(tmp_path / "stats.json"),
            },
            capture_output=True,
            text=True,
            timeout=45,
        )
        assert result.returncode == 0, result.stderr
        stats = json.loads((tmp_path / "stats.json").read_text())
        assert collection_result(result.returncode, stats).status == expected_status
        with repository.engine.connect() as connection:
            observation = dict(connection.execute(select(cards)).mappings().one())
        if expected_status == "failed":
            assert stats["item_dropped_count"] == 1
            assert stats["file_status_count/downloaded"] >= 1
            assert observation == previous_observation
        else:
            assert observation["name"] == "Nouvelle observation"
            assert observation["raw"] == {"observation": "replacement"}
            assert observation["updated_at"] > previous_observation["updated_at"]
            assert [image["path"] for image in observation["images"]] == image_paths
        if second_image == "replacement-back.png":
            colors = [(0, 128, 0) if expires == 0 else (255, 0, 0), (255, 255, 0)]
            for path, color in zip(image_paths, colors, strict=True):
                with Image.open(tmp_path / "images" / path) as image:
                    assert image.convert("RGB").getpixel((0, 0)) == color
        else:
            assert {
                path: (tmp_path / "images" / path).read_bytes() for path in image_paths
            } == previous_files
        assert sorted(
            str(path.relative_to(tmp_path / "images"))
            for path in (tmp_path / "images").rglob("*")
            if path.is_file()
        ) == sorted(image_paths)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        repository.close()
