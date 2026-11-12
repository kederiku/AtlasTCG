import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tcg_core.catalog.models import Card
from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata


@pytest.fixture
def repository(tmp_path):
    repository = Repository(f"sqlite:///{tmp_path / 'catalog.db'}")
    metadata.create_all(repository.engine)
    try:
        yield repository
    finally:
        repository.close()


@pytest.fixture
def populated_catalog(repository):
    for game, source, language, number, name in [
        ("pokemon", "tcgdex", "fr", "001", "Dracaufeu 100%_"),
        ("pokemon", "tcgdex", "fr", "002", "Dracaufeu 100%_"),
        ("pokemon", "tcgdex", "fr", "003", "Dracaufeu 1000x"),
        ("pokemon", "tcgdex", "en", "001", "Charizard 100%_"),
        ("pokemon", "other", "fr", "001", "Dracaufeu 100%_"),
        ("magic", "tcgdex", "fr", "001", "Autre jeu 100%_"),
    ]:
        repository.save(
            Card(
                game=game,
                source=source,
                language=language,
                source_id=f"base1-{number}",
                name=name,
                set_id="base1",
                number=number,
                source_url="https://example.com/card",
                set_info={"name": "Base", "block": {"id": "base", "name": "Bloc Base"}},
            ).model_dump(mode="json")
        )
    return repository


def test_search_pages_literal_matches_within_localized_filters(populated_catalog):
    repository = populated_catalog
    filters = {
        "q": "100%_",
        "game": "pokemon",
        "source": "tcgdex",
        "language": "fr",
        "set_id": "base1",
        "block_id": "base",
        "page_size": 1,
    }
    for page, expected_ids in [(1, ["base1-001"]), (2, ["base1-002"]), (3, [])]:
        result = repository.search(**filters, page=page)
        assert (result["total"], result["page"], result["page_size"]) == (2, page, 1)
        assert [item["source_id"] for item in result["items"]] == expected_ids
        for item in result["items"]:
            assert (item["game"], item["source"], item["language"]) == ("pokemon", "tcgdex", "fr")
            assert item["set_name"] == "Base"
            assert item["block_name"] == "Bloc Base"
            assert not {"raw", "faces", "game_data", "legalities"} & item.keys()
    assert repository.search(**(filters | {"block_id": "missing"}))["total"] == 0
    assert repository.search(**(filters | {"set_id": "missing"}))["items"] == []
    assert repository.search(q="dracaufeu")["total"] == 4
    assert (
        repository.get(game="pokemon", source="tcgdex", source_id="missing", language="fr") is None
    )


@pytest.mark.parametrize("batch_size", [1, 2])
def test_observation_batches_preserve_each_localized_identity(populated_catalog, batch_size):
    observations = list(populated_catalog.observations("tcgdex", batch_size=batch_size))
    assert [
        (row["game"], row["source"], row["source_id"], row["language"]) for row in observations
    ] == [
        ("magic", "tcgdex", "base1-001", "fr"),
        ("pokemon", "tcgdex", "base1-001", "en"),
        ("pokemon", "tcgdex", "base1-001", "fr"),
        ("pokemon", "tcgdex", "base1-002", "fr"),
        ("pokemon", "tcgdex", "base1-003", "fr"),
    ]
    assert list(populated_catalog.observations("missing", batch_size=batch_size)) == []


def test_rejected_card_does_not_leave_a_partial_set_or_block(repository):
    with repository.engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TRIGGER reject_card BEFORE INSERT ON cards "
                "BEGIN SELECT RAISE(ABORT, 'card rejected'); END"
            )
        )
    card = Card(
        game="pokemon",
        source="tcgdex",
        source_id="base1-004",
        language="fr",
        name="Dracaufeu",
        set_id="base1",
        number="004",
        source_url="https://example.com/card",
        set_info={"name": "Base", "block": {"id": "base", "name": "Bloc Base"}},
    )

    with pytest.raises(IntegrityError, match="card rejected"):
        repository.save(card.model_dump(mode="json"))

    assert repository.search()["total"] == 0
    assert repository.list_sets() == []
    assert repository.list_blocks() == []
