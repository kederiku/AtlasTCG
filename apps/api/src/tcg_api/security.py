"""Local administration constraints at the HTTP boundary."""

from fastapi import HTTPException, Request


def require_local_admin(request: Request) -> None:
    if request.headers.get("X-TCG-Admin") != "1":
        raise HTTPException(403, "Missing local admin header")
    origin = request.headers.get("origin")
    if origin and origin not in {
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    }:
        raise HTTPException(403, "Untrusted origin")
