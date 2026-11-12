"""Validate observations before media acquisition or persistence."""

from tcg_core.catalog.models import Card, LocalizedBlock, LocalizedSet


class ValidationPipeline:
    def process_item(self, item):
        model = {"set": LocalizedSet, "block": LocalizedBlock}.get(item.get("kind"), Card)
        return model.model_validate(item).model_dump(mode="json")
