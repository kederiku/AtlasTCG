from scrapy import Request
from tcg_scraping.fingerprints import ImageRequestFingerprinter


def test_shared_url_has_independent_destination_cache():
    fingerprinter = ImageRequestFingerprinter()
    one = Request("https://example.com/card", meta={"image_storage_path": "fr/1.webp"})
    two = one.replace(meta={"image_storage_path": "en/1.webp"})
    assert fingerprinter.fingerprint(one) != fingerprinter.fingerprint(two)
    assert fingerprinter.fingerprint(one) == fingerprinter.fingerprint(one.copy())
