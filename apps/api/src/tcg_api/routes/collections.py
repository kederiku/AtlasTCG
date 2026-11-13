"""HTTP adapter for submitting requests and consulting persisted jobs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from tcg_core.collections.connectors import CONNECTORS
from tcg_core.collections.models import JobRequest
from tcg_core.collections.queries import CollectionQueries
from tcg_core.collections.submission import RequestCollection

from tcg_api.schemas.collections import ConnectorView, JobView
from tcg_api.security import require_local_admin


def collection_routes(submission: RequestCollection, queries: CollectionQueries) -> APIRouter:
    router = APIRouter()

    @router.get("/api/spiders", response_model=list[ConnectorView])
    def connectors():
        return CONNECTORS

    @router.get("/api/jobs", response_model=list[JobView])
    def list_jobs():
        return queries.list()

    @router.post(
        "/api/jobs",
        status_code=202,
        response_model=JobView,
        dependencies=[Depends(require_local_admin)],
    )
    def enqueue_job(parameters: JobRequest):
        return submission.request(parameters)

    @router.get("/api/jobs/{identifier}", response_model=JobView)
    def get_job(identifier: UUID):
        job = queries.get(str(identifier))
        if job is None:
            raise HTTPException(404, "Collection not found")
        return job

    @router.get("/api/jobs/{identifier}/logs", response_class=PlainTextResponse)
    def logs(identifier: UUID) -> str:
        content = queries.logs(str(identifier))
        if content is None:
            raise HTTPException(404, "Collection not found")
        return content

    return router
