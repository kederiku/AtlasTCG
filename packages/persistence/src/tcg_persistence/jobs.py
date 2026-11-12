from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, String, Table, Text, insert, select, update
from sqlalchemy.engine import Engine
from tcg_core.collections.models import JobRecord, JobStatus

from tcg_persistence.schema import metadata

jobs = Table(
    "collection_jobs",
    metadata,
    Column("id", String, primary_key=True),
    Column("status", String, nullable=False, index=True),
    Column("parameters", JSON, nullable=False),
    Column("stats", JSON, nullable=False),
    Column("error", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("finished_at", DateTime(timezone=True), nullable=True),
)


class JobRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def enqueue(self, parameters: dict[str, Any]) -> JobRecord:
        record = JobRecord(
            id=str(uuid4()),
            status="queued",
            parameters=parameters,
            stats={},
            error=None,
            created_at=datetime.now(UTC),
            started_at=None,
            finished_at=None,
        )
        with self.engine.begin() as connection:
            connection.execute(insert(jobs).values(**record))
        return record

    def list(self) -> list[JobRecord]:
        with self.engine.connect() as connection:
            return [
                cast(JobRecord, dict(row))
                for row in connection.execute(
                    select(jobs).order_by(jobs.c.created_at.desc()).limit(50)
                ).mappings()
            ]

    def get(self, identifier: str) -> JobRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(jobs).where(jobs.c.id == identifier)).mappings().first()
            return cast(JobRecord, dict(row)) if row else None

    def claim(self) -> JobRecord | None:
        with self.engine.begin() as connection:
            identifier = connection.scalar(
                select(jobs.c.id)
                .where(jobs.c.status == "queued")
                .order_by(jobs.c.created_at)
                .limit(1)
            )
            if identifier is None:
                return None
            row = (
                connection.execute(
                    update(jobs)
                    .where(jobs.c.id == identifier, jobs.c.status == "queued")
                    .values(status="running", started_at=datetime.now(UTC))
                    .returning(*jobs.c)
                )
                .mappings()
                .first()
            )
            return cast(JobRecord, dict(row)) if row else None

    def finish(
        self, identifier: str, status: JobStatus, stats: dict[str, Any], error: str | None = None
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(jobs)
                .where(jobs.c.id == identifier)
                .values(status=status, stats=stats, error=error, finished_at=datetime.now(UTC))
            )

    def recover(self) -> None:
        # Called only after the single local worker lock has been acquired.
        with self.engine.begin() as connection:
            connection.execute(
                update(jobs)
                .where(jobs.c.status == "running")
                .values(
                    status="interrupted",
                    error="Worker interrupted; start a new collection to resume.",
                    finished_at=datetime.now(UTC),
                )
            )
