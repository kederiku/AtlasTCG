# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY apps/frontend/package.json apps/frontend/package-lock.json ./
RUN npm ci
COPY apps/frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.12.5 AS uv
FROM python:3.14.7-slim-bookworm AS runtime
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    TCG_IMAGES_DIR=/data/images \
    TCG_JOBS_DIR=/data/jobs/admin \
    PATH=/app/.venv/bin:$PATH
RUN groupadd --gid 1000 tcg \
    && useradd --uid 1000 --gid tcg --create-home tcg \
    && mkdir -p /data/images /data/jobs/admin \
    && chown -R tcg:tcg /data

# Workspace sources are build inputs only. Runtime images receive installed wheels.
FROM runtime AS workspace
COPY pyproject.toml uv.lock .python-version ./
COPY packages/core/pyproject.toml ./packages/core/pyproject.toml
COPY packages/core/src/ ./packages/core/src/
COPY packages/persistence/pyproject.toml ./packages/persistence/pyproject.toml
COPY packages/persistence/src/ ./packages/persistence/src/
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/api/src/ ./apps/api/src/
COPY apps/scraping/pyproject.toml ./apps/scraping/pyproject.toml
COPY apps/scraping/src/ ./apps/scraping/src/

FROM workspace AS api-install
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --package tcg-api --no-dev --no-editable

FROM workspace AS scraping-install
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --package tcg-scraping --no-dev --no-editable

FROM workspace AS migrate-install
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --package tcg-persistence --no-dev --no-editable

FROM runtime AS migrate
COPY --from=migrate-install /app/.venv /app/.venv
COPY alembic.ini ./
COPY packages/persistence/migrations/ ./packages/persistence/migrations/
USER tcg
CMD ["alembic", "upgrade", "head"]

FROM runtime AS scraping
COPY --from=scraping-install /app/.venv /app/.venv
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright \
    SCRAPY_SETTINGS_MODULE=tcg_scraping.settings
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*
USER tcg
CMD ["tcg-worker"]

FROM runtime AS api
COPY --from=api-install /app/.venv /app/.venv
COPY --from=frontend /build/frontend/dist ./frontend/dist
ENV TCG_FRONTEND_DIR=/app/frontend/dist
USER tcg
EXPOSE 8000
CMD ["uvicorn", "tcg_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
