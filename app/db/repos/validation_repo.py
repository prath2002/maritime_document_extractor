import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Validation


class ValidationRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **data: Any) -> Validation:
        record = Validation(**data)
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_by_id(self, validation_id: uuid.UUID) -> Validation | None:
        result = await self.session.execute(select(Validation).where(Validation.id == validation_id))
        return result.scalar_one_or_none()

    async def get_latest_for_session(self, session_id: uuid.UUID) -> Validation | None:
        result = await self.session.execute(
            select(Validation)
            .where(Validation.session_id == session_id)
            .order_by(Validation.created_at.desc(), Validation.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: uuid.UUID) -> Sequence[Validation]:
        result = await self.session.execute(
            select(Validation)
            .where(Validation.session_id == session_id)
            .order_by(Validation.created_at.desc(), Validation.id.desc())
        )
        return result.scalars().all()
