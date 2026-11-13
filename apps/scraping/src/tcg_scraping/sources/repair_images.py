"""Repair media on stored printings, discovering missing URLs only from TCGdex."""

import asyncio
from urllib.parse import quote

import scrapy
from scrapy import signals
from tcg_core.catalog.image_repair import ImageRepair
from tcg_persistence.catalog import Repository
from tcg_persistence.image_repair import SqlImageRepairStore

from tcg_scraping.image_repair import LocalImagePresence


class RepairImagesSpider(scrapy.Spider):
    name = "repair_images"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "ITEM_PIPELINES": {
            "tcg_scraping.image_repair.RepairImagesPipeline": 200,
            "tcg_scraping.image_repair.RepairPersistencePipeline": 300,
        },
    }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.repository = Repository(crawler.settings["DATABASE_URL"])
        spider.store = SqlImageRepairStore(spider.repository.engine)
        spider.repair = ImageRepair(
            spider.store, LocalImagePresence(crawler.settings["FILES_STORE"])
        )
        spider.capacity = asyncio.Semaphore(crawler.settings.getint("CONCURRENT_REQUESTS"))
        crawler.signals.connect(spider.close_resources, signal=signals.spider_closed)
        crawler.signals.connect(spider.item_failed, signal=signals.item_error)
        crawler.signals.connect(spider.item_failed, signal=signals.item_dropped)
        crawler.signals.connect(spider.completed, signal=signals.item_scraped)
        crawler.signals.connect(spider.request_dropped, signal=signals.request_dropped)
        return spider

    def close_resources(self):
        self.repository.close()

    def item_failed(self, item):
        self.crawler.stats.inc_value("images/errors")
        self.completed()

    def completed(self):
        self.capacity.release()

    def request_dropped(self, request):
        self.failed(request.cb_kwargs["candidate"], "Image discovery request was dropped")

    def identity(self, candidate):
        return f"{candidate.game}/{candidate.source}/{candidate.language}/{candidate.source_id}"

    def unavailable(self, candidate):
        self.crawler.stats.inc_value("images/unavailable")
        self.logger.info("Image unavailable: %s", self.identity(candidate))
        self.completed()

    def failed(self, candidate, error):
        self.crawler.stats.inc_value("images/errors")
        self.logger.error("Image repair failed for %s: %s", self.identity(candidate), error)
        self.completed()

    def item(self, plan):
        self.crawler.stats.inc_value("images/present", len(plan.images) - len(plan.downloads))
        return {"plan": plan, "source_id": self.identity(plan.candidate)}

    def discovery_url(self, candidate):
        return (
            f"https://api.tcgdex.net/v2/{quote(candidate.language, safe='')}/cards/"
            f"{quote(candidate.source_id, safe='')}"
        )

    async def start(self):
        for candidate in self.store.candidates():
            # SQL batching alone does not bound Scrapy's pending items/requests.
            await self.capacity.acquire()
            self.crawler.stats.inc_value("images/examined")
            try:
                plan = self.repair.plan(candidate)
            except Exception as error:
                self.failed(candidate, error)
                continue
            if not plan.needs_discovery:
                yield self.item(plan)
            elif (candidate.game, candidate.source) == ("pokemon", "tcgdex"):
                yield scrapy.Request(
                    self.discovery_url(candidate),
                    callback=self.parse_discovery,
                    cb_kwargs={"candidate": candidate},
                    errback=self.discovery_failed,
                    meta={"handle_httpstatus_list": [404]},
                )
            else:
                self.unavailable(candidate)

    def parse_discovery(self, response, candidate):
        if response.status == 404:
            self.unavailable(candidate)
            return
        try:
            data = response.json()
            if not isinstance(data, dict) or data.get("id") != candidate.source_id:
                raise ValueError("TCGdex response does not match the stored printing")
            source_image = data.get("image")
            if source_image is not None and not isinstance(source_image, str):
                raise ValueError("TCGdex image must be a URL string or null")
            if not source_image:
                self.unavailable(candidate)
                return
            plan = self.repair.discover(candidate, [source_image + "/high.webp"])
            if plan.needs_discovery:
                raise ValueError("TCGdex did not provide all missing image URLs")
            yield self.item(plan)
        except Exception as error:
            self.failed(candidate, error)

    def discovery_failed(self, failure):
        self.failed(failure.request.cb_kwargs["candidate"], failure.getErrorMessage())
