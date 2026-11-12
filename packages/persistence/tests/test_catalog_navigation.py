import pytest
from tcg_core.catalog.models import Card
from tcg_core.catalog.queries import CatalogService
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata


@pytest.fixture
def catalog(tmp_path):
    repository = Repository(f"sqlite:///{tmp_path / 'navigation.db'}")
    metadata.create_all(repository.engine)
    for game, source, languages in [
        ("pokemon", "tcgdex", ["fr", "es", "es-mx"]),
        ("pokemon", "other", ["en"]),
        ("magic", "tcgdex", ["fr"]),
    ]:
        for number in ("001", "002", "003"):
            for language in languages:
                repository.save(
                    Card(
                        game=game,
                        source=source,
                        source_id=f"bw4-{number}",
                        set_id="bw4",
                        number=number,
                        language=language,
                        name=f"{'Carta' if language == 'es' else 'Carte'} {number} 100%_",
                        source_url="https://example.com/card",
                        set_info={
                            "name": "Destinos Futuros" if language == "es" else "Destinées Futures",
                            "block": {
                                "id": "bw",
                                "name": "Negro y Blanco" if language == "es" else "Noir et Blanc",
                            },
                        },
                    ).model_dump(mode="json")
                )
    yield CatalogService(repository)
    repository.close()


def test_pages_count_groups_and_preserve_source_and_regional_identities(catalog):
    found = []
    for page in range(1, 6):
        result = catalog.browse(page=page, page_size=2, display_language="es")
        assert result["total"] == 9
        found.extend((c["game"], c["source"], c["source_id"]) for c in result["items"])
        for card in result["items"]:
            if card["game"] == "pokemon" and card["source"] == "tcgdex":
                assert card["language"] == "es"
                assert {v["language"] for v in card["versions"]} == {"fr", "es", "es-mx"}
    assert len(found) == len(set(found)) == 9
    assert catalog.browse(page=6, page_size=2)["items"] == []


@pytest.mark.parametrize("query", ["Destinos Futuros", "negro y blanco", "Carta", "100%_"])
def test_translations_find_groups_without_changing_card_language(catalog, query):
    result = catalog.browse(q=query, game="pokemon", source="tcgdex", language="fr")
    assert result["total"] == 3
    assert all(card["language"] == "fr" for card in result["items"])
    assert catalog.browse(q="1000x")["total"] == 0
    assert catalog.browse(q=query, language="ja")["items"] == []
    assert catalog.browse(q=query, block_id="missing")["total"] == 0
    assert catalog.browse(q=query, set_id="missing")["total"] == 0


def test_representative_respects_localized_set_and_block_filters(tmp_path):
    repository = Repository(f"sqlite:///{tmp_path / 'different.db'}")
    metadata.create_all(repository.engine)
    for language, set_id, block_id in [("fr", "first", "first"), ("es", "second", "second")]:
        repository.save(
            Card(
                game="pokemon",
                source="tcgdex",
                source_id="shared-1",
                name="Card",
                language=language,
                set_id=set_id,
                number="1",
                source_url="https://example.com",
                set_info={"block": {"id": block_id}},
            ).model_dump(mode="json")
        )
    service = CatalogService(repository)
    result = service.browse(display_language="fr", set_id="second", block_id="second")
    assert result["items"][0]["language"] == "es"
    assert len(result["items"][0]["versions"]) == 2
    assert service.browse(language="fr", set_id="second")["total"] == 0
    repository.close()
