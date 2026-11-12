import json


def test_tcgdex_discovers_each_block_once_per_language():
    from scrapy import Request
    from scrapy.http import TextResponse
    from tcg_scraping.sources.tcgdex.spider import TCGdexSpider

    spider = TCGdexSpider(languages="fr,en")
    requests = []
    for language, set_id in [("fr", "base1"), ("fr", "base2"), ("en", "base1")]:
        response = TextResponse(
            url=f"https://api.tcgdex.net/v2/{language}/sets/{set_id}",
            encoding="utf-8",
            body=json.dumps(
                {"id": set_id, "name": "Set", "serie": {"id": "base", "name": "Base"}}
            ).encode(),
        )
        requests.extend(
            item for item in spider.parse_set(response, language) if isinstance(item, Request)
        )
    assert [request.url for request in requests] == [
        "https://api.tcgdex.net/v2/fr/series/base",
        "https://api.tcgdex.net/v2/en/series/base",
    ]
