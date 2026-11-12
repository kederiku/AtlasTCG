"""Anti-corruption layer: TCGdex JSON → catalog domain, without network or SQL."""

from tcg_core.catalog.models import (
    Ability,
    BlockInfo,
    BlockReference,
    Card,
    CardFace,
    LocalizedBlock,
    LocalizedSet,
    ResourceCost,
    SetInfo,
    TextBlock,
)
from tcg_core.catalog.retention import without_prices


def normalize_set_info(data: dict) -> SetInfo:
    data = without_prices(data)
    count = data.get("cardCount") or {}
    series = data.get("serie") or {}
    return SetInfo(
        name=data.get("name"),
        block=BlockReference(id=series["id"], name=series.get("name"))
        if series.get("id")
        else None,
        release_date=data.get("releaseDate"),
        official_count=count.get("official"),
        total_count=count.get("total"),
        logo_url=data["logo"] + ".webp" if data.get("logo") else None,
        symbol_url=data["symbol"] + ".webp" if data.get("symbol") else None,
        raw=data,
    )


def normalize_set(data: dict, *, language: str) -> LocalizedSet:
    return LocalizedSet(
        game="pokemon",
        source="tcgdex",
        source_id=data["id"],
        language=language,
        info=normalize_set_info(data),
        is_complete=True,
    )


def normalize_block(data: dict, *, language: str) -> LocalizedBlock:
    return LocalizedBlock(
        game="pokemon",
        source="tcgdex",
        source_id=data["id"],
        language=language,
        info=BlockInfo(
            name=data.get("name"),
            logo_url=data["logo"] + ".webp" if data.get("logo") else None,
            raw=data,
        ),
        is_complete=True,
    )


def normalize_card(data: dict, *, language: str, source_url: str) -> Card:
    data = without_prices(data)
    illustrators = [data["illustrator"]] if data.get("illustrator") else []
    texts = [
        TextBlock(kind=kind, text=data[key])
        for key, kind in [("description", "flavor"), ("effect", "rules")]
        if data.get(key)
    ]
    abilities = []
    for key, kind in [("abilities", "ability"), ("attacks", "attack")]:
        for value in data.get(key) or []:
            abilities.append(
                Ability(
                    kind=kind,
                    name=value.get("name"),
                    text=value.get("effect"),
                    cost=ResourceCost(symbols=value["cost"]) if "cost" in value else None,
                    damage=str(value["damage"]) if value.get("damage") is not None else None,
                    attributes={
                        k: v
                        for k, v in value.items()
                        if k not in {"name", "effect", "cost", "damage"}
                    },
                )
            )
    face = CardFace(
        name=data["name"],
        types=[data["category"]] if data.get("category") else [],
        traits={
            key: value if isinstance(value, list) else [value]
            for key in ("types", "stage", "suffix", "trainerType", "energyType")
            if (value := data.get(key)) is not None
        },
        texts=texts,
        statistics={"hp": data["hp"]} if data.get("hp") is not None else {},
        costs={"retreat": ResourceCost(value=data["retreat"])} if "retreat" in data else {},
        abilities=abilities,
        illustrators=illustrators,
        image_index=0 if data.get("image") else None,
    )
    specific = {
        key: data[key]
        for key in (
            "dexId",
            "evolveFrom",
            "weaknesses",
            "resistances",
            "regulationMark",
            "variants",
            "variants_detailed",
            "thirdParty",
            "updated",
        )
        if key in data
    }
    return Card(
        game="pokemon",
        source="tcgdex",
        source_id=data["id"],
        language=language,
        name=data["name"],
        set_id=data["set"]["id"],
        number=data["localId"],
        source_url=source_url,
        set_info=normalize_set_info(data["set"]),
        image_urls=[data["image"] + "/high.webp"] if data.get("image") else [],
        rarity=data.get("rarity"),
        illustrators=illustrators,
        faces=[face],
        legalities={
            key: "legal" if value else "not_legal"
            for key, value in (data.get("legal") or {}).items()
            if isinstance(value, bool)
        },
        game_data={"pokemon": specific},
        raw=data,
    )
