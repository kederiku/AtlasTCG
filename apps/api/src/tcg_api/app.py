"""Composition root: assemble adapters and own their lifetime."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware
from tcg_core.catalog.queries import CatalogService
from tcg_core.collections.discovery import CollectionDiscovery, CollectionOptions
from tcg_core.collections.queries import CollectionQueries
from tcg_core.collections.submission import RequestCollection
from tcg_persistence.catalog import Repository
from tcg_persistence.configuration import database_url as configured_database_url
from tcg_persistence.jobs import JobRepository

from tcg_api.discovery import TCGdexDiscovery
from tcg_api.logs import FileJobLogs
from tcg_api.routes.catalog import catalog_routes
from tcg_api.routes.collection_options import collection_option_routes
from tcg_api.routes.collections import collection_routes
from tcg_api.routes.health import health_routes
from tcg_api.static import mount_files


def create_app(
    database_url: str | None = None,
    images_dir: str | Path | None = None,
    jobs_dir: str | Path | None = None,
    *,
    frontend_dir: str | Path | None = None,
    discovery: CollectionDiscovery | None = None,
) -> FastAPI:
    images = Path(images_dir or os.getenv("TCG_IMAGES_DIR", "data/images"))
    images.mkdir(parents=True, exist_ok=True)
    jobs = Path(jobs_dir or os.getenv("TCG_JOBS_DIR", "data/jobs/admin"))
    frontend = frontend_dir or os.getenv("TCG_FRONTEND_DIR")
    repository = Repository(database_url or configured_database_url())
    job_store = JobRepository(repository.engine)
    http_discovery = TCGdexDiscovery() if discovery is None else None
    choice_source = discovery if discovery is not None else http_discovery
    assert choice_source is not None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if http_discovery is not None:
                http_discovery.close()
            repository.close()

    app = FastAPI(title="TCG Catalog Admin", lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )
    app.include_router(health_routes(repository.is_ready))
    app.include_router(catalog_routes(CatalogService(repository)))
    app.include_router(collection_option_routes(CollectionOptions(choice_source)))
    app.include_router(
        collection_routes(
            RequestCollection(job_store), CollectionQueries(job_store, FileJobLogs(jobs))
        )
    )
    mount_files(app, images, Path(frontend) if frontend else None)
    return app
