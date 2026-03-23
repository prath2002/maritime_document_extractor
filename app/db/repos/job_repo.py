import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job


class JobRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **data: Any) -> Job:
        record = Job(**data)
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: uuid.UUID) -> Sequence[Job]:
        result = await self.session.execute(
            select(Job).where(Job.session_id == session_id).order_by(Job.queued_at.asc(), Job.id.asc())
        )
        return result.scalars().all()

    async def list_pending_for_session(self, session_id: uuid.UUID) -> Sequence[Job]:
        return await self.list_by_status_for_session(session_id, statuses=("QUEUED", "PROCESSING"))

    async def list_by_status(self, statuses: Sequence[str]) -> Sequence[Job]:
        result = await self.session.execute(
            select(Job).where(Job.status.in_(tuple(statuses))).order_by(Job.queued_at.asc(), Job.id.asc())
        )
        return result.scalars().all()

    async def list_by_status_for_session(
        self, session_id: uuid.UUID, *, statuses: Sequence[str]
    ) -> Sequence[Job]:
        result = await self.session.execute(
            select(Job)
            .where(Job.session_id == session_id)
            .where(Job.status.in_(tuple(statuses)))
            .order_by(Job.queued_at.asc(), Job.id.asc())
        )
        return result.scalars().all()
