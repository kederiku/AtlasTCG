"""Copy legacy images into the new layout and update their database references.

Run with `uv run --env-file .env python -m tcg_persistence.migrate_images --apply`.
Without --apply, only display the proposed changes. Originals are kept as a backup.
"""

import argparse
import os
import shutil
from pathlib import Path

from sqlalchemy import select, update
from tcg_core.catalog.media import image_path

from tcg_persistence.catalog import Repository
from tcg_persistence.configuration import database_url as configured_database_url
from tcg_persistence.schema import cards


def migrate(repository, root, *, apply=False):
    root = Path(root).resolve()
    changed = 0
    with repository.engine.begin() as connection:
        rows = connection.execute(select(cards)).mappings()
        for row in rows:
            images = []
            modified = False
            for index, asset in enumerate(row["images"]):
                target = image_path(row, index)
                images.append(asset | {"path": target})
                if asset["path"] == target:
                    continue
                source_path = (root / asset["path"]).resolve()
                target_path = (root / target).resolve()
                if not source_path.is_relative_to(root) or not target_path.is_relative_to(root):
                    raise ValueError("Image path escapes storage directory")
                if not source_path.is_file():
                    raise FileNotFoundError(source_path)
                if target_path.exists() and source_path.read_bytes() != target_path.read_bytes():
                    raise FileExistsError(f"Conflicting image: {target_path}")
                print(f"{asset['path']} -> {target}")
                if apply:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    if not target_path.exists():
                        shutil.copy2(source_path, target_path)
                modified = True
            if modified:
                changed += 1
                if apply:
                    connection.execute(
                        update(cards)
                        .where(
                            cards.c.game == row["game"],
                            cards.c.source == row["source"],
                            cards.c.source_id == row["source_id"],
                            cards.c.language == row["language"],
                        )
                        .values(images=images)
                    )
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    repository = Repository(configured_database_url())
    try:
        count = migrate(repository, os.getenv("TCG_IMAGES_DIR", "data/images"), apply=args.apply)
        print(f"{count} card(s) {'updated' if args.apply else 'to update'}.")
    finally:
        repository.close()


if __name__ == "__main__":
    main()
