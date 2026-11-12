def test_migration_keeps_originals_updates_db_and_is_idempotent(tmp_path):
    from sqlalchemy import select
    from tcg_persistence.catalog import Repository
    from tcg_persistence.migrate_images import migrate
    from tcg_persistence.schema import cards, metadata

    repository = Repository(f"sqlite:///{tmp_path / 'catalog.db'}")
    metadata.create_all(repository.engine)
    root = tmp_path / "images"
    root.mkdir()
    (root / "old.webp").write_bytes(b"legacy-file")
    repository.save(
        dict(
            game="pokemon",
            source="tcgdex",
            source_id="base1-4",
            language="fr",
            name="Dracaufeu",
            set_id="base1",
            number="4",
            source_url="https://example.com",
            image_urls=["https://example.com/image"],
            images=[{"path": "old.webp", "url": "https://example.com/image", "checksum": "kept"}],
            raw={},
        )
    )
    assert migrate(repository, root) == 1
    assert not (root / "pokemon").exists()
    assert migrate(repository, root, apply=True) == 1
    assert migrate(repository, root, apply=True) == 0
    target = "pokemon/fr/base1/4-base1.webp"
    assert (root / target).read_bytes() == (root / "old.webp").read_bytes()
    with repository.engine.connect() as connection:
        asset = connection.execute(select(cards.c.images)).scalar_one()[0]
        assert asset["path"] == target
        assert asset["checksum"] == "kept"
    repository.close()
