"""Keep collectible/gameplay data; exclude monetary valuation fields recursively."""

import re
from typing import Any

_MONETARY_KEYS = {
    "price",
    "prices",
    "pricing",
    "cardprices",
    "pricehistory",
    "priceguide",
    "marketprice",
    "marketvalue",
    "lowprice",
    "midprice",
    "highprice",
    "directlowprice",
    "purchaseprice",
    "saleprice",
    "buyprice",
    "sellprice",
    "averageprice",
    "usd",
    "usdfoil",
    "usdetched",
    "eur",
    "eurfoil",
    "tix",
}


def without_prices(value: Any) -> Any:
    """Return a copy. Gameplay costs, text, statistics and vendor IDs are retained."""
    if isinstance(value, dict):
        return {
            key: without_prices(child)
            for key, child in value.items()
            if re.sub(r"[^a-z0-9]", "", str(key).lower()) not in _MONETARY_KEYS
        }
    if isinstance(value, list):
        return [without_prices(child) for child in value]
    return value
