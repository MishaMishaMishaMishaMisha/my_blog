from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx import ASGITransport
from sqlalchemy import text
from sqlalchemy import delete
from source.main import app
from source.database.db_connect import (
    async_engine,
    async_session_factory,
)
from source.models.base import BaseORMModel
from sqlalchemy import text
from unittest.mock import patch
from source.services.email import EmailService



# Автоматический мок для отправки писем во всех тестах
@pytest.fixture(autouse=True)
def mock_email_service():
    with patch.object(EmailService, "sendEmail", return_value=None) as mock_send:
        yield mock_send
        
    

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_pg_extensions():
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
    yield

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_and_drop_tables():
    
    async with async_engine.begin() as conn:
        await conn.run_sync(BaseORMModel.metadata.create_all)

    yield

    async with async_engine.begin() as conn:
        await conn.run_sync(BaseORMModel.metadata.drop_all)
        

@pytest_asyncio.fixture
async def db_session():
    async with async_session_factory() as session:
        yield session
        
        
@pytest_asyncio.fixture
async def async_client():

    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test") as client:

        yield client
        

# путь к папке с медиа файлами для тестов 
@pytest.fixture(scope="session")
def test_media_dir():

    return Path(__file__).parent.parent / "media"

# путь куда будут загружаться медиа файлы (tmp_path это встроенная в pytest. файлы потом сами будут удалены)
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
