import re
from urllib.parse import quote, unquote

import scrapy
from tcg_core.collections.models import CollectionScope

from tcg_scraping.middleware import CardAlreadyStored
from tcg_scraping.sources.tcgdex.normalize import normalize_block, normalize_card, normalize_set


class TCGdexSpider(scrapy.Spider):
    name = "tcgdex"
    # Documented public API, used as an API client rather than a website crawler.
    # https://tcgdex.dev/rest and https://tcgdex.dev/assets
    custom_settings = {"ROBOTSTXT_OBEY": False}
    allowed_domains = ["api.tcgdex.net", "assets.tcgdex.net"]
    api_url = "https://api.tcgdex.net/v2"

    def __init__(
        self,
        languages="fr,en",
        card_ids="",
        limit=None,
        force="false",
        block_id="",
        set_id="",
        **kwargs,
    ):
        super().__init__(**kwargs)
        if (block_id and set_id) or ((block_id or set_id) and (card_ids or limit is not None)):
            raise ValueError("Choose one scope, without card_ids or limit")
        self.scope = (
            CollectionScope(kind="block" if block_id else "set", id=block_id or set_id)
            if block_id or set_id
            else None
        )
        self.languages = list(dict.fromkeys(languages.split(",")))
        self.card_ids = [value for value in card_ids.split(",") if value]
        if str(force).lower() not in {"true", "false", "1", "0"}:
            raise ValueError("force must be true or false")
        self.force = str(force).lower() in {"true", "1"}
        self.requested_sets = set()
        self.requested_blocks = set()
        self.limit = int(limit) if limit is not None else (0 if self.scope else 10)
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
        return f"{self.api_url}/{language}/cards" + (
            f"/{quote(card_id, safe='')}" if card_id else ""
        )

    async def start(self):
        for language in self.languages:
            if self.scope:
                yield self.metadata_request(
                    self.scope.kind, language, self.scope.id, expand=True, root=True
                )
            elif self.card_ids:
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

    def parse_card(self, response, language, expected_set=None):
        data = response.json()
        if expected_set is not None:
            self.validate_identity(data, unquote(response.url.rsplit("/", 1)[1]))
            if not isinstance(data.get("set"), dict) or data["set"].get("id") != expected_set:
                raise ValueError("TCGdex card does not belong to the requested extension")
        yield normalize_card(data, language=language, source_url=response.url).model_dump(
            mode="json"
        )
        set_id = data["set"]["id"]
        key = (language, set_id)
        if key not in self.requested_sets:
            yield self.metadata_request("set", language, set_id)

    def metadata_request(self, kind, language, identifier, *, expand=False, root=False):
        requested = self.requested_sets if kind == "set" else self.requested_blocks
        requested.add((language, identifier))
        resource = "sets" if kind == "set" else "series"
        return scrapy.Request(
            f"{self.api_url}/{language}/{resource}/{quote(identifier, safe='')}",
            callback=self.parse_set if kind == "set" else self.parse_block,
            cb_kwargs={"language": language, "expand": expand},
            meta={"scope_root": root},
            errback=self.request_failed if self.scope else None,
        )

    def parse_set(self, response, language, expand=False):
        data = response.json()
        if self.scope:
            self.validate_identity(data, unquote(response.url.rsplit("/", 1)[1]))
        if expand:
            card_ids = self.listed_ids(data, "cards")
            self.record_root(response, language)
        observation = normalize_set(data, language=language)
        yield observation.model_dump(mode="json")
        block = observation.info.block
        if block and (language, block.id) not in self.requested_blocks:
            yield self.metadata_request("block", language, block.id)
        if expand:
            for card_id in card_ids:
                yield scrapy.Request(
                    self.endpoint(language, card_id),
                    meta=self.card_meta(language, card_id),
                    callback=self.parse_card,
                    cb_kwargs={"language": language, "expected_set": data["id"]},
                    errback=self.request_failed,
                )

    def parse_block(self, response, language, expand=False):
        data = response.json()
        if self.scope:
            self.validate_identity(data, unquote(response.url.rsplit("/", 1)[1]))
        if expand:
            set_ids = self.listed_ids(data, "sets")
            self.record_root(response, language)
        yield normalize_block(data, language=language).model_dump(mode="json")
        if expand:
            for set_id in set_ids:
                if (language, set_id) not in self.requested_sets:
                    yield self.metadata_request("set", language, set_id, expand=True)

    @staticmethod
    def validate_identity(data, expected):
        if not isinstance(data, dict) or data.get("id") != expected:
            raise ValueError("TCGdex returned a different resource identity")

    @staticmethod
    def listed_ids(data, field):
        entries = data.get(field)
        if not isinstance(entries, list):
            raise ValueError(f"TCGdex {field} must be a list")
        identifiers = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"Invalid TCGdex {field} entry")
            identifier = CollectionScope(kind="set", id=entry.get("id")).id
            if identifier not in identifiers:
                identifiers.append(identifier)
        return identifiers

    def record_root(self, response, language):
        if response.meta.get("scope_root"):
            self.crawler.stats.inc_value("scope/languages_found")
            self.logger.info("Scope available in %s", language)

    def request_failed(self, failure):
        if failure.check(CardAlreadyStored):
            return
        request = failure.request
        response = getattr(failure.value, "response", None)
        if request.meta.get("scope_root") and response is not None and response.status == 404:
            self.crawler.stats.inc_value("scope/languages_unavailable")
            self.logger.warning("Scope unavailable: %s", request.url)
        else:
            self.logger.error("Scope resource failed: %s (%s)", request.url, failure.value)

    def closed(self, reason):
        if self.scope and not self.crawler.stats.get_value("scope/languages_found", 0):
            self.logger.error("Scope unavailable in all requested languages")
