import pytest
import pytest_asyncio

from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from unittest.mock import patch

from source.main import create_app
from source.database.db_connect import async_engine, async_session_factory
from source.models.base import BaseORMModel
from source.services.email import EmailService
from source.api.v1.dependencies.rate_limit import disable_all_rate_limiters


# Автоматический мок для отправки писем во всех тестах
@pytest.fixture(autouse=True)
def mock_email_service():
    with patch.object(EmailService, "sendEmail", return_value=None) as mock_send:
        yield mock_send
        

# создание расширения для поиска в бд
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_pg_extensions():
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
    yield
    

# создание и очистка таблиц в бд
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_and_drop_tables():
    
    async with async_engine.begin() as conn:
        await conn.run_sync(BaseORMModel.metadata.create_all)

    yield

    async with async_engine.begin() as conn:
        await conn.run_sync(BaseORMModel.metadata.drop_all)
        

# бд сессия
@pytest_asyncio.fixture
async def db_session():
    async with async_session_factory() as session:
        yield session
        

# приложение fastapi
@pytest.fixture(scope="session", autouse=True)
def test_app():
    app = create_app(with_lifespan=False)

    disable_all_rate_limiters(app)
    yield app

    app.dependency_overrides.clear()
        

# клиент для отправки запросов
@pytest_asyncio.fixture
async def async_client(test_app):

    async with AsyncClient(transport=ASGITransport(app=test_app),
                           base_url="http://test") as client:

        yield client
        

# путь к папке с медиа файлами для тестов 
@pytest.fixture(scope="session")
def test_media_dir():

    return Path(__file__).parent.parent / "media"


# путь куда будут загружаться медиа файлы 
# (tmp_path это встроенная в pytest. файлы потом сами будут удалены)
@pytest.fixture
def temp_upload_dir(tmp_path):

    upload_dir = tmp_path / "uploads"

    upload_dir.mkdir()

    return upload_dir



from tests.integration.fixtures.users import *
from tests.integration.fixtures.auth import *
from tests.integration.fixtures.tags import *
from tests.integration.fixtures.uploads import *
from tests.integration.fixtures.posts import *
from tests.integration.fixtures.comments import *
