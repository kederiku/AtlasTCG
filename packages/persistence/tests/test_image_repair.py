from datetime import UTC, datetime

from sqlalchemy import select
from tcg_core.catalog.image_repair import ImageAsset, ImageRepair, RepairCandidate
from tcg_persistence.catalog import Repository
from tcg_persistence.image_repair import SqlImageRepairStore
from tcg_persistence.schema import cards, metadata, sets


class MissingFiles:
    def exists(self, path):
        return False


def test_repair_updates_only_media_on_the_selected_localized_printing(tmp_path):
    repository = Repository(f"sqlite:///{tmp_path / 'catalog.db'}")
    metadata.create_all(repository.engine)
    try:
        for language in ("fr", "es"):
            repository.save(
                {
                    "game": "pokemon",
                    "source": "tcgdex",
                    "source_id": "base1-4",
                    "language": language,
                    "name": "Observation conservée",
                    "set_id": "base1",
                    "number": "4",
                    "source_url": "https://example.com/previous",
                    "image_urls": [],
                    "images": [],
                    "raw": {"name": "Original"},
                    "updated_at": datetime(2024, 1, 2, tzinfo=UTC),
                },
                preserve_updated_at=True,
            )
        with repository.engine.connect() as connection:
            before = [
                dict(row)
                for row in connection.execute(select(cards).order_by(cards.c.language)).mappings()
            ]
            sets_before = [dict(row) for row in connection.execute(select(sets)).mappings()]
        candidate = RepairCandidate.model_validate(before[0])
        store = SqlImageRepairStore(repository.engine)
        service = ImageRepair(store, MissingFiles())
        plan = service.discover(candidate, ["https://assets.example/new.webp"])
        with repository.engine.connect() as connection:
            discovered = connection.execute(
                select(cards.c.image_urls).where(cards.c.language == "es")
            ).scalar_one()
        assert discovered == ["https://assets.example/new.webp"]
        assert not plan.needs_discovery
        assert len(plan.downloads) == 1
        service.complete(
            plan,
            [ImageAsset(path="pokemon/es/base1/4-base1.webp", url=discovered[0], checksum="new")],
        )
        with repository.engine.connect() as connection:
            after = [
                dict(row)
                for row in connection.execute(select(cards).order_by(cards.c.language)).mappings()
            ]
            assert [dict(row) for row in connection.execute(select(sets)).mappings()] == sets_before
        assert after[0]["images"][0]["checksum"] == "new"
        assert {k: v for k, v in after[0].items() if k not in {"image_urls", "images"}} == {
            k: v for k, v in before[0].items() if k not in {"image_urls", "images"}
        }
        assert after[1] == before[1]
        assert [(row.source_id, row.language) for row in store.candidates(batch_size=1)] == [
            ("base1-4", "es"),
            ("base1-4", "fr"),
        ]
    finally:
        repository.close()
