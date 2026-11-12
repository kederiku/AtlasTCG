def test_common_contract_supports_multiface_cards_and_symbolic_resources():
    from tcg_core.catalog.models import Card, CardFace, ResourceCost, TextBlock

    for game in ("magic", "one-piece", "naruto", "yugioh", "cyberpunk", "altered", "riftbound"):
        # Synthetic contract examples, not imported or official cards for these games.
        card = Card(
            game=game,
            source="fixture",
            source_id="x",
            language="en",
            name="Example",
            set_id="set",
            number="001",
            source_url="https://example.com",
            faces=[
                CardFace(
                    name="Front",
                    statistics={"power": "*", "defense": 0},
                    costs={"play": ResourceCost(symbols=["{X}", "{R}"])},
                    texts=[TextBlock(kind="rules", text="A rule.")],
                ),
                CardFace(name="Back", statistics={"power": 4}),
            ],
        )
        assert Card.model_validate_json(card.model_dump_json()) == card
        assert "hp" not in card.faces[0].statistics
        assert card.faces[1].costs == {}
