import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Extraction


class ExtractionRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **data: Any) -> Extraction:
        record = Extraction(**data)
        self.session.add(record)
        await self.session.flush()
        return record

    async def create_or_get_existing(self, **data: Any) -> tuple[Extraction, bool]:
        statement = (
            pg_insert(Extraction.__table__)
            .values(**data)
            .on_conflict_do_nothing(index_elements=["session_id", "file_hash"])
            .returning(Extraction.id)
        )
        result = await self.session.execute(statement)
        inserted_id = result.scalar_one_or_none()

        if inserted_id is not None:
            created = await self.get_by_id(inserted_id)
            if created is None:
                raise RuntimeError("Inserted extraction could not be reloaded.")
            return created, True

        existing = await self.find_by_session_and_hash(data["session_id"], data["file_hash"])
        if existing is None:
            raise RuntimeError("Existing extraction could not be reloaded after conflict.")

        return existing, False

    async def get_by_id(self, extraction_id: uuid.UUID) -> Extraction | None:
        result = await self.session.execute(select(Extraction).where(Extraction.id == extraction_id))
        return result.scalar_one_or_none()

    async def find_by_session_and_hash(
        self, session_id: uuid.UUID, file_hash: str
    ) -> Extraction | None:
        result = await self.session.execute(
            select(Extraction)
            .where(Extraction.session_id == session_id)
            .where(Extraction.file_hash == file_hash)
        )
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: uuid.UUID) -> Sequence[Extraction]:
        result = await self.session.execute(
            select(Extraction)
            .where(Extraction.session_id == session_id)
            .order_by(Extraction.created_at.asc(), Extraction.id.asc())
        )
        return result.scalars().all()
