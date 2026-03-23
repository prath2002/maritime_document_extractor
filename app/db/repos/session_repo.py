import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session


class SessionRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, session_id: uuid.UUID | None = None) -> Session:
        record = Session(id=session_id or uuid.uuid4())
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        result = await self.session.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def exists(self, session_id: uuid.UUID) -> bool:
        return await self.get_by_id(session_id) is not None
