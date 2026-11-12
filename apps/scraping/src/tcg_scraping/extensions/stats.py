import json
from pathlib import Path

from scrapy import signals


class AdminStats:
    def __init__(self, crawler):
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        extension = cls(crawler)
        crawler.signals.connect(extension.finished, signal=signals.engine_stopped)
        return extension

    def finished(self):
        destination = self.crawler.settings.get("ADMIN_STATS_PATH")
        if destination:
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.crawler.stats.get_stats(), default=str))
            temporary.replace(path)
