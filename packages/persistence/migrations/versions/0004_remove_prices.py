"""Permanently remove monetary data, including nested raw payloads and variants.

The retention policy is frozen here so future application changes cannot change
what this migration does. No schema change; downgrade cannot recreate deleted data.
"""

import re

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_KEYS = {
    "price",
    "prices",
    "pricing",
    "cardprices",
    "pricehistory",
    "priceguide",
    "marketprice",
    "marketvalue",
    "lowprice",
    "midprice",
    "highprice",
    "directlowprice",
    "purchaseprice",
    "saleprice",
    "buyprice",
    "sellprice",
    "averageprice",
    "usd",
    "usdfoil",
    "usdetched",
    "eur",
    "eurfoil",
    "tix",
}


def _clean(value):
    if isinstance(value, dict):
        return {
            key: _clean(child)
            for key, child in value.items()
            if re.sub(r"[^a-z0-9]", "", str(key).lower()) not in _KEYS
        }
    if isinstance(value, list):
        return [_clean(child) for child in value]
    return value


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Avoid a partial-set merge reading old JSON while this cleanup is committing.
        bind.execute(sa.text("LOCK TABLE localized_sets, cards IN ACCESS EXCLUSIVE MODE"))
    for name, documents in [
        ("cards", ("raw", "game_data", "faces", "legalities")),
        ("localized_sets", ("info",)),
    ]:
        table = sa.Table(name, sa.MetaData(), autoload_with=bind)
        identity = list(table.primary_key.columns)
        last = None
        while True:
            query = sa.select(*identity, *(table.c[key] for key in documents))
            if last is not None:
                query = query.where(sa.tuple_(*identity) > last)
            rows = bind.execute(query.order_by(*identity).limit(200)).mappings().all()
            if not rows:
                break
            for row in rows:
                changes = {
                    key: cleaned for key in documents if (cleaned := _clean(row[key])) != row[key]
                }
                if changes:
                    bind.execute(
                        table.update()
                        .where(*(column == row[column.name] for column in identity))
                        .values(**changes)
                    )
            last = tuple(rows[-1][column.name] for column in identity)


def downgrade():
    raise RuntimeError("Price removal is irreversible; restore an earlier backup if required.")
