"""Exercise real downloader, media pipeline and database without an external API."""

import functools
import http.server
import os
import subprocess
import sys
import threading

from PIL import Image
from sqlalchemy import create_engine, select
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import cards, metadata


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
