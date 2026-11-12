"""Declarative capabilities shared by clients, without loading a spider."""

from typing import TypedDict


class ConnectorSpec(TypedDict):
    id: str
    name: str
    game: str
    languages: list[str]


CONNECTORS: list[ConnectorSpec] = [
    {
        "id": "tcgdex",
        "name": "TCGdex",
        "game": "pokemon",
        "languages": [
            "en",
            "fr",
            "es",
            "es-mx",
            "it",
            "pt",
            "pt-br",
            "pt-pt",
            "de",
            "nl",
            "pl",
            "ru",
            "ja",
            "ko",
            "zh-tw",
            "id",
            "th",
            "zh-cn",
        ],
    }
]
