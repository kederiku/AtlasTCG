"""Repair media on existing localized printings without replacing observations."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter

from tcg_core.catalog.media import image_path


class ImageAsset(BaseModel):
    model_config = ConfigDict(extra="allow")
    path: str
    url: str | None = None
    checksum: str | None = None
    status: str | None = None


class RepairCandidate(BaseModel):
    game: str
    source: str
    source_id: str
    language: str
    set_id: str
    number: str
    image_urls: list[HttpUrl] = Field(default_factory=list)
    images: list[ImageAsset] = Field(default_factory=list)


@dataclass(frozen=True)
class ImageDownload:
    index: int
    url: str
    path: str


@dataclass(frozen=True)
class RepairPlan:
    candidate: RepairCandidate
    images: tuple[ImageAsset, ...] = ()
    downloads: tuple[ImageDownload, ...] = ()
    needs_discovery: bool = False


class ImagePresence(Protocol):
    def exists(self, path: str) -> bool: ...


class ImageRepairStore(Protocol):
    def candidates(self) -> Iterable[RepairCandidate]: ...
    def update_image_urls(self, candidate: RepairCandidate, urls: Sequence[str]) -> None: ...
    def update_images(self, candidate: RepairCandidate, images: Sequence[ImageAsset]) -> None: ...


class ImageRepair:
    def __init__(self, store: ImageRepairStore, files: ImagePresence) -> None:
        self.store = store
        self.files = files

    def plan(self, candidate: RepairCandidate) -> RepairPlan:
        images = []
        downloads = []
        needs_discovery = False
        for index in range(max(len(candidate.image_urls), len(candidate.images), 1)):
            asset = (
                candidate.images[index]
                if index < len(candidate.images)
                else ImageAsset(path=image_path(candidate.model_dump(), index))
            )
            images.append(asset)
            if self.files.exists(asset.path):
                continue
            url = (
                str(candidate.image_urls[index]) if index < len(candidate.image_urls) else asset.url
            )
            if url:
                downloads.append(ImageDownload(index, url, asset.path))
            else:
                needs_discovery = True
        return RepairPlan(candidate, tuple(images), tuple(downloads), needs_discovery)

    def discover(self, candidate: RepairCandidate, urls: Sequence[str]) -> RepairPlan:
        validated = TypeAdapter(list[HttpUrl]).validate_python(list(urls))
        if validated:
            self.store.update_image_urls(candidate, [str(url) for url in validated])
        return self.plan(candidate.model_copy(update={"image_urls": validated}))

    def complete(self, plan: RepairPlan, downloaded: Sequence[ImageAsset]) -> None:
        if plan.needs_discovery or len(downloaded) != len(plan.downloads):
            raise ValueError("Image repair is incomplete")
        images = list(plan.images)
        for target, asset in zip(plan.downloads, downloaded, strict=True):
            if target.path != asset.path:
                raise ValueError("Downloaded image does not match its destination")
            images[target.index] = asset
        if images != plan.candidate.images:
            self.store.update_images(plan.candidate, images)
