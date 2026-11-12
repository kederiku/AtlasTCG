from tcg_persistence.catalog import Repository
from tcg_persistence.schema import metadata
from tcg_scraping.sources.tcgdex.normalize import normalize_set


def test_full_block_metadata_survives_partial_set_summaries(tmp_path):
    from tcg_scraping.sources.tcgdex.normalize import normalize_block

    repository = Repository(f"sqlite:///{tmp_path / 'metadata.db'}")
    metadata.create_all(repository.engine)
    repository.save_block(
        normalize_block(
            {
                "id": "base",
                "name": "Bloc Base",
                "logo": "https://assets.example.com/base/logo",
                "pricing": {"usd": 42},
                "sets": [{"id": "base1", "name": "Set de Base"}],
            },
            language="fr",
        )
    )
    repository.save_set(
        normalize_set(
            {
                "id": "base1",
                "name": "Set de Base",
                "serie": {"id": "base", "name": "Base"},
            },
            language="fr",
        )
    )
    block = repository.list_blocks()[0]
    assert block["name"] == "Bloc Base"
    assert block["info"]["logo_url"] == "https://assets.example.com/base/logo.webp"
    assert "pricing" not in block["info"]["raw"]
    assert repository.list_sets()[0]["info"]["block"]["name"] == "Bloc Base"
    repository.close()
