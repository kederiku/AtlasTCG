"""Readiness is supplied by the composition root."""

from collections.abc import Callable

from fastapi import APIRouter, HTTPException


def health_routes(is_ready: Callable[[], bool]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/health")
    def health() -> dict[str, str]:
        if not is_ready():
            raise HTTPException(503, "Catalog database unavailable")
        return {"status": "ok"}

    return router
