import pytest
from tcg_core.catalog.image_repair import ImageRepair, RepairCandidate


class Files:
    def __init__(self, *paths):
        self.paths = set(paths)

    def exists(self, path):
        return path in self.paths


class Store:
    def update_image_urls(self, candidate, urls):
        self.urls = urls

    def update_images(self, candidate, images):
        self.images = images


def candidate(**changes):
    return RepairCandidate.model_validate(
        {
            "game": "pokemon",
            "source": "tcgdex",
            "source_id": "base1-4",
            "language": "fr",
            "set_id": "base1",
            "number": "4",
            "image_urls": ["https://assets.example/front.webp", "https://assets.example/back.webp"],
            "images": [],
        }
        | changes
    )


def test_only_missing_faces_are_selected_and_existing_metadata_is_preserved():
    front = {"path": "pokemon/fr/base1/4-base1.webp", "checksum": "previous", "status": "cached"}
    card = candidate(images=[front])
    plan = ImageRepair(Store(), Files(front["path"])).plan(card)
    assert not plan.needs_discovery
    assert [(image.index, image.url, image.path) for image in plan.downloads] == [
        (1, "https://assets.example/back.webp", "pokemon/fr/base1/4-base1-image-2.webp")
    ]
    assert plan.images[0].model_dump(exclude_unset=True) == front


@pytest.mark.parametrize("urls", [[], ["https://assets.example/front.webp"]])
def test_unreferenced_existing_file_is_reused_without_discovery(urls):
    path = "pokemon/fr/base1/4-base1.webp"
    plan = ImageRepair(Store(), Files(path)).plan(candidate(image_urls=urls))
    assert not plan.needs_discovery
    assert plan.downloads == ()
    assert plan.images[0].path == path


def test_missing_url_requires_discovery_only_when_the_file_is_absent():
    plan = ImageRepair(Store(), Files()).plan(candidate(image_urls=[]))
    assert plan.needs_discovery
    assert plan.downloads == ()
