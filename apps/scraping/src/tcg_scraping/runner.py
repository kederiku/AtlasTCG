"""Execute a validated request in an isolated Scrapy process, never a shell."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from tcg_core.collections.models import CollectionRequest, CollectionResult


def collection_result(returncode: int, stats: dict[str, Any]) -> CollectionResult:
    failed = (
        returncode != 0
        or stats.get("finish_reason") != "finished"
        or stats.get("log_count/ERROR", 0)
        or stats.get("item_dropped_count", 0)
    )
    return CollectionResult(
        status="failed" if failed else "succeeded",
        stats=stats,
        error="Collection failed; inspect logs." if failed else None,
    )


class ScrapyCollector:
    def __init__(self, jobs_dir: str | Path, *, timeout: float = 3600) -> None:
        self.jobs_dir = Path(jobs_dir).resolve()
        self.timeout = timeout

    def command(self, identifier: str, request: CollectionRequest) -> list[str]:
        return [
            sys.executable,
            "-m",
            "scrapy",
            "crawl",
            request.spider,
            "-a",
            f"languages={','.join(request.languages)}",
            "-a",
            f"card_ids={','.join(request.card_ids)}",
            "-a",
            f"limit={request.limit}",
            "-a",
            f"force={str(request.force).lower()}",
            "-s",
            "LOG_LEVEL=INFO",
            "-s",
            f"ADMIN_STATS_PATH={self.jobs_dir / identifier / 'stats.json'}",
        ]

    def run(self, identifier: str, request: CollectionRequest) -> CollectionResult:
        directory = self.jobs_dir / identifier
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "crawl.log").open("wb") as log:
            process = subprocess.Popen(
                self.command(identifier, request),
                stdout=log,
                stderr=subprocess.STDOUT,
                env=os.environ | {"SCRAPY_SETTINGS_MODULE": "tcg_scraping.settings"},
            )
            try:
                code = process.wait(timeout=self.timeout)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
        stats_file = directory / "stats.json"
        stats = json.loads(stats_file.read_text()) if stats_file.exists() else {}
        return collection_result(code, stats)
