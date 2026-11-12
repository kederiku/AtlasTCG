"""Read the bounded tail of a collection log from shared local storage."""

from pathlib import Path


class FileJobLogs:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def read(self, identifier: str) -> str:
        path = self.directory / identifier / "crawl.log"
        try:
            with path.open("rb") as file:
                file.seek(0, 2)
                file.seek(max(0, file.tell() - 64000))
                return file.read().decode("utf-8", errors="replace")
        except FileNotFoundError:
            return "En attente du worker…"
