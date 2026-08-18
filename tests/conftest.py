import pytest_asyncio
import pytest

from sqlalchemy import text

from source.core.config import settings
from source.database.db_connect import async_engine


# проверка на MODE=TEST и успешное подключение к бд

@pytest.fixture(scope="session", autouse=True)
def check_mode():
    if settings.MODE != "TEST":
        pytest.exit("MODE is not TEST")

@pytest_asyncio.fixture(scope="session", autouse=True)
async def check_database():
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            if result.scalar() != 1:
                raise RuntimeError("SELECT 1 returned unexpected result")
    except Exception as e:
        pytest.exit(f"PostgreSQL is unavailable: Error: {e}")
