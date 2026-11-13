"""Skip known card detail requests before robots.txt or HTTP downloads."""

from scrapy import signals
from scrapy.exceptions import IgnoreRequest
from tcg_persistence.catalog import Repository


class CardAlreadyStored(IgnoreRequest):
    """An intentional skip, distinct from a failed acquisition."""


class SkipExistingCardsMiddleware:
    def __init__(self, repository, stats):
        self.repository = repository
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(Repository(crawler.settings["DATABASE_URL"]), crawler.stats)
        crawler.signals.connect(middleware.close, signal=signals.spider_closed)
        return middleware

    def process_request(self, request):
        identity = request.meta.get("card_identity")
        if identity and not request.meta.get("force_refresh", False):
            if self.repository.contains(**identity):
                self.stats.inc_value("cards/skipped_existing")
                raise CardAlreadyStored(f"Card already stored: {identity}")

    def close(self):
        self.repository.close()
