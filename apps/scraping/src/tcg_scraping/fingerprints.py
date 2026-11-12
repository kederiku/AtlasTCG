"""Scrapy request identity includes the destination of each media file."""

import hashlib

from scrapy.utils.request import RequestFingerprinter


class ImageRequestFingerprinter(RequestFingerprinter):
    def fingerprint(self, request):
        original = super().fingerprint(request)
        path = request.meta.get("image_storage_path")
        if path is None:
            return original
        # A shared URL must still produce a file for each destination card/language.
        return hashlib.sha256(original + path.encode()).digest()
