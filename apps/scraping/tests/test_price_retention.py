import json
from pathlib import Path

from tcg_scraping.sources.tcgdex.normalize import normalize_card, normalize_set


def test_import_discards_prices_at_every_depth_but_keeps_gameplay_costs():
    raw = json.loads(Path("tests/fixtures/tcgdex_charizard.json").read_text())
    raw["pricing"] = {"cardmarket": {"avg": 450}}
    raw["variants_detailed"] = [
        {"variantId": "holo", "pricing": {"usd": 50}, "thirdParty": {"cardmarket": 123}}
    ]
    raw["set"]["prices"] = {"eur": 3}
    raw["future"] = [{"card_prices": [{"usd": "10"}], "name": "keep"}]
    card = normalize_card(raw, language="fr", source_url="https://example.com")
    assert "pricing" not in card.raw
    assert "pricing" not in card.game_data["pokemon"]
    assert card.raw["variants_detailed"] == [
        {"variantId": "holo", "thirdParty": {"cardmarket": 123}}
    ]
    assert card.raw["future"] == [{"name": "keep"}]
    assert "prices" not in card.set_info.raw
    assert card.faces[0].costs["retreat"].value == 3
    assert card.faces[0].abilities[1].cost.symbols == ["Feu"] * 4
    assert "pricing" in raw  # Never mutate the caller's response.
    extension = normalize_set(
        {"id": "base1", "name": "Base", "cards": [{"id": "x", "price": 30}]}, language="en"
    )
    assert extension.info.raw["cards"] == [{"id": "x"}]
