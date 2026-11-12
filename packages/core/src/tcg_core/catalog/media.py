"""Stable, filesystem-safe image names shared by downloads and migrations."""

import hashlib
import re
from collections.abc import Mapping


def component(value: object) -> str:
    text = str(value)
    if re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", text):
        return text
    # Keep identifiers readable, without collapsing distinct unsafe identifiers.
    readable = re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_")[:60] or "unknown"
    return f"{readable}-{hashlib.sha256(text.encode()).hexdigest()[:12]}"


def image_path(card: Mapping[str, object], index: int = 0) -> str:
    game, language, set_id, number = (
        component(card[key]) for key in ("game", "language", "set_id", "number")
    )
    suffix = f"-image-{index + 1}" if index else ""
    return f"{game}/{language}/{set_id}/{number}-{set_id}{suffix}.webp"
