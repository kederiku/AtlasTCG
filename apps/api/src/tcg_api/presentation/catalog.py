"""Project catalog observations into HTTP representations without modifying them."""

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote


def present_card(card: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(card) | {
        "source_image_urls": card["image_urls"],
        "image_urls": ["/api/images/" + quote(asset["path"], safe="/") for asset in card["images"]],
    }
    if "versions" in card:
        result["versions"] = [present_card(version) for version in card["versions"]]
    return result


def present_page(page: Mapping[str, Any]) -> dict[str, Any]:
    return dict(page) | {"items": [present_card(card) for card in page["items"]]}
