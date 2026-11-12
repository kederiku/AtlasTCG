"""Choose a collected language without changing a printing's identity."""

from collections.abc import Iterable


def preferred_language(languages: Iterable[str], preferred: str) -> str:
    available = set(languages)
    for language in (preferred, "fr", "en", *sorted(available)):
        if language in available:
            return language
    raise ValueError("A card group must contain a matching printing")
