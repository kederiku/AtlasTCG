from pathlib import PurePosixPath

from tcg_core.catalog.media import component, image_path


def test_layout_and_faces():
    card = dict(game="pokemon", language="fr", set_id="base1", number="004")
    assert image_path(card) == "pokemon/fr/base1/004-base1.webp"
    assert image_path(card, 1) == "pokemon/fr/base1/004-base1-image-2.webp"
    assert image_path(card | {"game": "lorcana", "language": "en"}) == (
        "lorcana/en/base1/004-base1.webp"
    )


def test_unsafe_identifiers_are_safe_and_distinct():
    for value in ("../outside", "/etc/passwd", "..", "", "123/198", "étoile", "a" * 500):
        part = component(value)
        assert len(PurePosixPath(part).parts) == 1
        assert part not in {".", ".."}
        assert len(part) < 100
    assert component("123/198") != component("123_198")
