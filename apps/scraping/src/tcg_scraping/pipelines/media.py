"""Download each media destination and store a lossless WebP."""

import hashlib
from io import BytesIO

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
        return deferToThread(self._convert_and_store, response, request, info, item)

    def _convert_and_store(self, response, request, info, item):
        body = encode_webp(response.body)
        path = self.file_path(request, response=response, info=info, item=item)
        self.store.persist_file(
            path, BytesIO(body), info, meta=None, headers={"Content-Type": "image/webp"}
        )
        return hashlib.sha256(body).hexdigest()

    def item_completed(self, results, item, info):
        if item.get("kind") in {"set", "block"}:
            return item
        item["images"] = [result for success, result in results if success]
        if any(not success for success, _ in results):
            raise DropItem(f"Image download/conversion failed: {item['source_id']}")
        return item
