"""Download each media destination and store a lossless WebP."""

import hashlib
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from threading import Lock

from PIL import Image, ImageOps
from scrapy import Request
from scrapy.exceptions import DropItem
from scrapy.pipelines.files import FilesPipeline
from tcg_core.catalog.media import image_path
from twisted.internet.threads import deferToThread


def encode_webp(body):
    with Image.open(BytesIO(body)) as original:
        original.load()
        image = ImageOps.exif_transpose(original).convert("RGBA")
        output = BytesIO()
        image.save(output, format="WEBP", lossless=True, method=6)
        return output.getvalue()


class WebPImagesPipeline(FilesPipeline):
    @classmethod
    def from_crawler(cls, crawler):
        pipeline = super().from_crawler(crawler)
        pipeline.staging = TemporaryDirectory(prefix=".pending-webp-", dir=pipeline.store.basedir)
        pipeline.publish_lock = Lock()
        return pipeline

    def get_media_requests(self, item, info):
        if item.get("kind") in {"set", "block"}:
            return []
        return [
            Request(url, meta={"image_storage_path": image_path(item, index)})
            for index, url in enumerate(item["image_urls"])
        ]

    def file_path(self, request, response=None, info=None, *, item=None):
        return request.meta["image_storage_path"]

    def file_downloaded(self, response, request, info, *, item=None):
        return deferToThread(self._convert_and_stage, response, request)

    def _convert_and_stage(self, response, request):
        body = encode_webp(response.body)
        with NamedTemporaryFile(dir=self.staging.name, delete=False) as staged:
            staged.write(body)
            request.meta["webp_staging_path"] = staged.name
        return hashlib.sha256(body).hexdigest()

    async def media_downloaded(self, response, request, info, *, item=None):
        result = await super().media_downloaded(response, request, info, item=item)
        result["webp_staging_path"] = request.meta.pop("webp_staging_path")
        return result

    def item_completed(self, results, item, info):
        if item.get("kind") in {"set", "block"}:
            return item
        if any(not success for success, _ in results):
            raise DropItem(f"Image download/conversion failed: {item['source_id']}")
        return deferToThread(self._publish, [result for _, result in results], item, info)

    def _publish(self, results, item, info):
        # Scrapy's filesystem store caches mkdir calls without thread synchronization.
        with self.publish_lock:
            for result in results:
                staged = result.get("webp_staging_path")
                if staged:
                    self.store.persist_file(
                        result["path"],
                        BytesIO(Path(staged).read_bytes()),
                        info,
                        meta=None,
                        headers={"Content-Type": "image/webp"},
                    )
        item["images"] = [
            {key: value for key, value in result.items() if key != "webp_staging_path"}
            for result in results
        ]
        return item

    def close_spider(self):
        # Cached Scrapy results can be reused by another item until the crawl ends.
        self.staging.cleanup()
