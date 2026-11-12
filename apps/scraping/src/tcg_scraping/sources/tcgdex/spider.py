import re
from urllib.parse import quote

import scrapy

from tcg_scraping.sources.tcgdex.normalize import normalize_block, normalize_card, normalize_set


class TCGdexSpider(scrapy.Spider):
    name = "tcgdex"
    # Documented public API, used as an API client rather than a website crawler.
    # https://tcgdex.dev/rest and https://tcgdex.dev/assets
    custom_settings = {"ROBOTSTXT_OBEY": False}
    allowed_domains = ["api.tcgdex.net", "assets.tcgdex.net"]

    def __init__(self, languages="fr,en", card_ids="", limit="10", force="false", **kwargs):
        super().__init__(**kwargs)
        self.languages = list(dict.fromkeys(languages.split(",")))
        self.card_ids = [value for value in card_ids.split(",") if value]
        if str(force).lower() not in {"true", "false", "1", "0"}:
            raise ValueError("force must be true or false")
        self.force = str(force).lower() in {"true", "1"}
        self.requested_sets = set()
        self.requested_blocks = set()
        self.limit = int(limit)
        if self.limit < 0:
            raise ValueError("limit must be >= 0 (0 = all)")
        if not all(
            re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]+)*", language) for language in self.languages
        ):
            raise ValueError("languages must be comma-separated language codes")

    def card_meta(self, language, card_id):
        return {
            "card_identity": {
                "game": "pokemon",
                "source": "tcgdex",
                "source_id": card_id,
                "language": language,
            },
            "force_refresh": self.force,
        }

    def endpoint(self, language, card_id=""):
        return f"https://api.tcgdex.net/v2/{language}/cards" + (
            f"/{quote(card_id, safe='')}" if card_id else ""
        )

    async def start(self):
        for language in self.languages:
            if self.card_ids:
                for card_id in self.card_ids[: self.limit or None]:
                    yield scrapy.Request(
                        self.endpoint(language, card_id),
                        meta=self.card_meta(language, card_id),
                        callback=self.parse_card,
                        cb_kwargs={"language": language},
                    )
            else:
                yield scrapy.Request(
                    self.endpoint(language), callback=self.parse, cb_kwargs={"language": language}
                )

    def parse(self, response, language):
        for card in response.json()[: self.limit or None]:
            yield scrapy.Request(
                self.endpoint(language, card["id"]),
                meta=self.card_meta(language, card["id"]),
                callback=self.parse_card,
                cb_kwargs={"language": language},
            )

    def parse_card(self, response, language):
        data = response.json()
        yield normalize_card(data, language=language, source_url=response.url).model_dump(
            mode="json"
        )
        set_id = data["set"]["id"]
        key = (language, set_id)
        if key not in self.requested_sets:
            self.requested_sets.add(key)
            yield scrapy.Request(
                f"https://api.tcgdex.net/v2/{language}/sets/{quote(set_id, safe='')}",
                callback=self.parse_set,
                cb_kwargs={"language": language},
            )

    def parse_set(self, response, language):
        observation = normalize_set(response.json(), language=language)
        yield observation.model_dump(mode="json")
        block = observation.info.block
        if block and (language, block.id) not in self.requested_blocks:
            self.requested_blocks.add((language, block.id))
            yield scrapy.Request(
                f"https://api.tcgdex.net/v2/{language}/series/{quote(block.id, safe='')}",
                callback=self.parse_block,
                cb_kwargs={"language": language},
            )

    def parse_block(self, response, language):
        yield normalize_block(response.json(), language=language).model_dump(mode="json")
