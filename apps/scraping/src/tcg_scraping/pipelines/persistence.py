"""Persist validated observations in short transactions."""

from tcg_core.catalog.models import LocalizedBlock, LocalizedSet
from tcg_persistence.catalog import Repository


class DatabasePipeline:
    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.stats = crawler.stats
        pipeline.repository = Repository(crawler.settings["DATABASE_URL"])
        return pipeline

    def process_item(self, item):
        # One short transaction per card; image conversion runs outside the reactor.
        if item.get("kind") == "block":
            self.repository.save_block(LocalizedBlock.model_validate(item))
            self.stats.inc_value("blocks/stored")
        elif item.get("kind") == "set":
            self.repository.save_set(LocalizedSet.model_validate(item))
            self.stats.inc_value("sets/stored")
        else:
            self.repository.save(item)
            self.stats.inc_value("cards/stored")
        return item

    def close_spider(self):
        self.repository.close()
