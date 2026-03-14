"""Supabase keep-alive — run via cron every 5 days."""
import asyncio

from sqlalchemy import text

from app.core.database import init_engine, _get_session_factory
from app.core.logging import setup_logging


async def main():
    setup_logging()
    init_engine()
    factory = _get_session_factory()
    async with factory() as session:
        result = await session.execute(text("SELECT 1"))
        print(f"Keep-alive ping: {result.scalar()}")


if __name__ == "__main__":
    asyncio.run(main())
