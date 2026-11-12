"""Framework-free operations must work when framework imports are unavailable."""

import subprocess
import sys


def test_image_naming_works_without_scrapy():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import importlib.abc
import sys
class NoScrapy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] == 'scrapy':
            raise ImportError('Scrapy is not installed in this application')
sys.meta_path.insert(0, NoScrapy())
from tcg_core.catalog.media import image_path
assert image_path(dict(game='pokemon', language='fr', set_id='base1', number='004')) == \
    'pokemon/fr/base1/004-base1.webp'
""",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
