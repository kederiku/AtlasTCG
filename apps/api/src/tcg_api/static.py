"""Serve media and an optional frontend build on the API origin."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_files(app: FastAPI, images: Path, frontend: Path | None) -> None:
    app.mount("/api/images", StaticFiles(directory=images), name="images")
    if frontend is None or not frontend.is_dir():
        return

    @app.get("/collections", include_in_schema=False)
    @app.get("/cards/{game}/{source}/{language}/{source_id:path}", include_in_schema=False)
    def admin_page() -> FileResponse:
        return FileResponse(frontend / "index.html")

    app.mount("/", StaticFiles(directory=frontend, html=True), name="admin")
