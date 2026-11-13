"""Filesystem and Scrapy pipeline adapters for image repairs."""

from pathlib import Path

from scrapy import Request
from tcg_core.catalog.image_repair import ImageAsset

from tcg_scraping.pipelines.media import WebPImagesPipeline


class LocalImagePresence:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def exists(self, path):
        destination = (self.root / path).resolve()
        if Path(path).is_absolute() or not destination.is_relative_to(self.root):
            raise ValueError("Image path escapes configured storage")
        if destination.exists() and not destination.is_file():
            raise ValueError("Image destination is not a file in storage")
        return destination.is_file()


class RepairImagesPipeline(WebPImagesPipeline):
    def get_media_requests(self, item, info):
        return [
            Request(target.url, meta={"image_storage_path": target.path})
            for target in item["plan"].downloads
        ]


class RepairPersistencePipeline:
    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def process_item(self, item):
        self.crawler.spider.repair.complete(
            item["plan"], [ImageAsset.model_validate(asset) for asset in item["images"]]
        )
        self.crawler.stats.inc_value("images/downloaded", len(item["plan"].downloads))
        return item
