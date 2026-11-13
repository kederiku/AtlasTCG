"""Read repair candidates and update only their media columns."""

from sqlalchemy import select, tuple_, update
from tcg_core.catalog.image_repair import RepairCandidate

from tcg_persistence.schema import cards

IDENTITY = ("game", "source", "source_id", "language")


class SqlImageRepairStore:
    def __init__(self, engine):
        self.engine = engine

    def update_image_urls(self, candidate, urls):
        with self.engine.begin() as connection:
            connection.execute(
                update(cards)
                .where(*(cards.c[key] == getattr(candidate, key) for key in IDENTITY))
                .values(image_urls=list(urls))
            )

    def update_images(self, candidate, images):
        with self.engine.begin() as connection:
            connection.execute(
                update(cards)
                .where(*(cards.c[key] == getattr(candidate, key) for key in IDENTITY))
                .values(images=[asset.model_dump(exclude_unset=True) for asset in images])
            )

    def candidates(self, batch_size=200):
        columns = [cards.c[key] for key in IDENTITY]
        last = None
        while True:
            statement = (
                select(*columns, cards.c.set_id, cards.c.number, cards.c.image_urls, cards.c.images)
                .order_by(*columns)
                .limit(batch_size)
            )
            if last is not None:
                statement = statement.where(tuple_(*columns) > last)
            with self.engine.connect() as connection:
                rows = connection.execute(statement).mappings().all()
            if not rows:
                return
            for row in rows:
                yield RepairCandidate.model_validate(dict(row))
            last = tuple(rows[-1][key] for key in IDENTITY)
