import asyncio
import json
from io import BytesIO

import pytest
from PIL import Image
from scrapy.http import TextResponse
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata
from tcg_scraping.pipelines.media import encode_webp
from tcg_scraping.sources.tcgdex.spider import TCGdexSpider


def observation(language="fr"):
    return {
        "game": "pokemon",
        "source": "tcgdex",
        "source_id": "base1-4",
        "language": language,
        "name": "Dracaufeu",
        "set_id": "base1",
        "number": "4",
        "source_url": "https://api.tcgdex.net/v2/fr/cards/base1-4",
        "image_urls": [],
        "images": [],
        "raw": {},
    }


def test_webp_preserves_size_and_pixels():
    source = Image.new("RGBA", (31, 47), (42, 84, 126, 127))
    data = BytesIO()
    source.save(data, format="PNG")
    with Image.open(BytesIO(encode_webp(data.getvalue()))) as result:
        assert result.format == "WEBP"
        assert result.size == source.size
        assert result.convert("RGBA").tobytes() == source.tobytes()


def test_corrupt_image_is_rejected():
    with pytest.raises(OSError):
        encode_webp(b"not an image")


def test_tcgdex_mapping_and_missing_image():
    spider = TCGdexSpider()
    data = {"id": "base1-4", "name": "Dracaufeu", "localId": "4", "set": {"id": "base1"}}
    response = TextResponse(
        url=spider.endpoint("fr", "base1-4"), body=json.dumps(data).encode(), encoding="utf-8"
    )
    card = next(spider.parse_card(response, "fr"))
    assert card["language"] == "fr"
    assert card["image_urls"] == []
    assert card["raw"] == data


def test_list_limit_and_language():
    spider = TCGdexSpider(limit="2")
    response = TextResponse(
        url=spider.endpoint("fr"),
        body=json.dumps([{"id": str(i)} for i in range(5)]).encode(),
        encoding="utf-8",
    )
    requests = list(spider.parse(response, "fr"))
    assert len(requests) == 2
    assert requests[0].cb_kwargs == {"language": "fr"}


def test_regional_language_codes_survive_requests_and_observations():
    languages = ["es-mx", "pt", "pt-br", "pt-pt", "zh-tw", "zh-cn"]
    spider = TCGdexSpider(languages=",".join(languages), card_ids="base1-4", limit="1")

    async def start_requests():
        return [request async for request in spider.start()]

    requests = asyncio.run(start_requests())
    assert len(requests) == len(languages)
    data = {"id": "base1-4", "name": "Charizard", "localId": "4", "set": {"id": "base1"}}
    for language, request in zip(languages, requests, strict=True):
        assert request.url == f"https://api.tcgdex.net/v2/{language}/cards/base1-4"
        assert request.meta["card_identity"]["language"] == language
        response = TextResponse(url=request.url, body=json.dumps(data).encode(), encoding="utf-8")
        card = next(spider.parse_card(response, **request.cb_kwargs))
        assert card["language"] == language
        assert card["source_url"] == request.url


def test_existing_card_filter_scopes_identity_and_force(tmp_path):
    from scrapy import Request
    from scrapy.crawler import Crawler
    from scrapy.exceptions import IgnoreRequest
    from scrapy.statscollectors import MemoryStatsCollector
    from tcg_scraping.middleware import SkipExistingCardsMiddleware

    repository = Repository(f"sqlite:///{tmp_path / 'catalog.db'}")
    metadata.create_all(repository.engine)
    repository.save(observation())
    stats = MemoryStatsCollector(Crawler(TCGdexSpider))
    middleware = SkipExistingCardsMiddleware(repository, stats)
    spider = TCGdexSpider()
    identity = spider.card_meta("fr", "base1-4")["card_identity"]

    def request(key, force=False):
        return Request("https://example.com", meta={"card_identity": key, "force_refresh": force})

    with pytest.raises(IgnoreRequest):
        middleware.process_request(request(identity))
    assert stats.get_value("cards/skipped_existing") == 1
    for field, value in [
        ("language", "en"),
        ("source", "other"),
        ("game", "other"),
        ("source_id", "new"),
    ]:
        assert middleware.process_request(request(identity | {field: value})) is None
    assert middleware.process_request(request(identity, force=True)) is None
    assert middleware.process_request(Request("https://example.com/list")) is None
    assert TCGdexSpider(force="true").card_meta("fr", "base1-4")["force_refresh"] is True
    middleware.close()


@pytest.mark.parametrize("explicit_ids", [False, True], ids=["discovery", "explicit-ids"])
@pytest.mark.parametrize(
    ("limit", "expected_downloads"),
    [
        ("2", []),
        ("0", [("fr", "base1-3"), ("en", "base1-3")]),
    ],
    ids=["bounded-candidates", "unlimited-cli"],
)
def test_candidate_limit_precedes_existing_filter_without_backfilling(
    tmp_path, explicit_ids, limit, expected_downloads
):
    from scrapy.crawler import Crawler
    from scrapy.exceptions import IgnoreRequest
    from scrapy.statscollectors import MemoryStatsCollector
    from tcg_scraping.middleware import SkipExistingCardsMiddleware

    repository = Repository(f"sqlite:///{tmp_path / 'candidates.db'}")
    metadata.create_all(repository.engine)
    for language in ("fr", "en"):
        for number in ("1", "2"):
            repository.save(
                observation(language) | {"source_id": f"base1-{number}", "number": number}
            )
    stats = MemoryStatsCollector(Crawler(TCGdexSpider))
    middleware = SkipExistingCardsMiddleware(repository, stats)
    try:
        # Repeating a bounded request must inspect the same first candidates,
        # rather than advancing to the third card because the first two exist.
        for attempt in (1, 2):
            spider = TCGdexSpider(
                languages="fr,en",
                card_ids="base1-1,base1-2,base1-3" if explicit_ids else "",
                limit=limit,
            )

            async def start_requests(candidate_spider):
                return [request async for request in candidate_spider.start()]

            requests = asyncio.run(start_requests(spider))
            if not explicit_ids:
                requests = [
                    candidate
                    for listing in requests
                    for candidate in spider.parse(
                        TextResponse(
                            url=listing.url,
                            body=b'[{"id":"base1-1"},{"id":"base1-2"},{"id":"base1-3"}]',
                            encoding="utf-8",
                        ),
                        **listing.cb_kwargs,
                    )
                ]
            downloads = []
            for request in requests:
                try:
                    middleware.process_request(request)
                except IgnoreRequest:
                    continue
                identity = request.meta["card_identity"]
                downloads.append((identity["language"], identity["source_id"]))

            assert downloads == expected_downloads
            assert stats.get_value("cards/skipped_existing") == 4 * attempt
            assert repository.search()["total"] == 4
    finally:
        middleware.close()


def test_tcgdex_api_policy_is_scoped_to_spider():
    from scrapy.settings import Settings
    from tcg_scraping import settings

    assert settings.ROBOTSTXT_OBEY is True
    configured = Settings({"ROBOTSTXT_OBEY": True})
    TCGdexSpider.update_settings(configured)
    assert configured.getbool("ROBOTSTXT_OBEY") is False
