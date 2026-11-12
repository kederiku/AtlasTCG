"""Run the installed Scrapy project from any working directory."""

import os

from scrapy.cmdline import execute


def main() -> None:
    os.environ["SCRAPY_SETTINGS_MODULE"] = "tcg_scraping.settings"
    execute()


if __name__ == "__main__":
    main()
