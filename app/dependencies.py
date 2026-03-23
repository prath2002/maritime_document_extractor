from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db_session
from app.llm.base import LLMProvider
from app.queue.manager import QueueManager


async def get_database_session() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


def get_queue_manager(request: Request) -> QueueManager:
    return request.app.state.queue_manager


def get_llm_provider(request: Request) -> LLMProvider | None:
    return request.app.state.llm_provider
