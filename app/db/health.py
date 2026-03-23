from sqlalchemy import text

from app.db.base import get_engine


async def ping_database() -> None:
    async with get_engine().connect() as connection:
        await connection.execute(text("SELECT 1"))
