import pytest_asyncio
import pytest
import asyncio

from sqlalchemy import text

from source.core.config import settings
from source.database.db_connect import async_engine

    
# проверка на MODE=TEST и успешное подключение к бд
def pytest_sessionstart(session):
    
    if settings.MODE != "TEST":
        pytest.exit("MODE is not TEST")
    
    try:
        asyncio.run(check_database())
    except Exception as e:
        pytest.exit(f"PostgreSQL is unavailable: Error: {e}. db_url={settings.db.url_asyncpg}")
        
async def check_database():
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))

        if result.scalar() != 1:
            raise RuntimeError("SELECT 1 returned unexpected result")
