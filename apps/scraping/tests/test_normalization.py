import json
from pathlib import Path

from tcg_scraping.sources.tcgdex.normalize import normalize_card


def test_pokemon_mapping_preserves_printed_meaning_and_localized_set():
    raw = json.loads(Path("tests/fixtures/tcgdex_charizard.json").read_text())
    card = normalize_card(
        raw, language="fr", source_url="https://api.tcgdex.net/v2/fr/cards/base1-4"
    )
    assert card.set_info.name == "Set de Base"
    assert card.illustrators == ["Mitsuhiro Arita"]
    face = card.faces[0]
    assert face.statistics["hp"] == 120
    attack = next(ability for ability in face.abilities if ability.kind == "attack")
    assert attack.damage == "100+"
    assert attack.cost.symbols == ["Feu"] * 4
    assert "Défaussez" in attack.text
    assert face.costs["retreat"].value == 3
    assert face.texts[0].kind == "flavor"
    assert card.game_data["pokemon"]["weaknesses"] == [{"type": "Eau", "value": "×2"}]
    assert card.raw == raw


def test_missing_is_not_zero_and_trainer_rules_are_not_flavor():
    data = {
        "id": "x-01",
        "localId": "01",
        "name": "Trainer",
        "set": {"id": "x"},
        "category": "Trainer",
        "effect": "Draw 2 cards.",
    }
    card = normalize_card(data, language="en", source_url="https://example.com")
    assert "hp" not in card.faces[0].statistics
    assert card.set_info.name is None
    assert card.faces[0].texts[0].kind == "rules"
    assert (
        normalize_card(
            data | {"hp": 0, "retreat": 0}, language="en", source_url="https://example.com"
        )
        .faces[0]
        .costs["retreat"]
        .value
        == 0
    )
