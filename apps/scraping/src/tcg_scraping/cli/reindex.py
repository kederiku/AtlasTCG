"""Offline catalog enrichment: preview by default, --apply to persist."""

import argparse

from tcg_core.catalog.reindex import reindex
from tcg_persistence.catalog import Repository
from tcg_persistence.configuration import database_url as configured_database_url

from tcg_scraping.sources.tcgdex.normalize import normalize_card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    repository = Repository(configured_database_url())
    try:
        result = reindex(repository, normalize_card, source="tcgdex", apply=args.apply)
        print(
            f"{'Updated' if args.apply else 'Would update'}: {result.updated}; "
            f"already current: {result.skipped}; invalid observations: {result.failed}"
        )
        if result.failed:
            raise SystemExit(1)
    finally:
        repository.close()


if __name__ == "__main__":
    main()
