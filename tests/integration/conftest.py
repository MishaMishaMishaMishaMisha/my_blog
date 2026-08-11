from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx import ASGITransport
from sqlalchemy import text
from sqlalchemy import delete
from source.main import create_app
from source.database.db_connect import (
    async_engine,
    async_session_factory,
)
from source.models.base import BaseORMModel
from sqlalchemy import text
from unittest.mock import patch
from source.services.email import EmailService

from source.dependencies.rate_limit import (register_rate_limiter,
                                            get_me_limiter,
                                            get_users_limiter,
                                            find_users_limiter,
                                            get_user_profile_limiter,
                                            get_user_posts_limiter,
                                            delete_user_limiter,
                                            update_user_limiter,
                                            login_limiter,
                                            logout_limiter,
                                            refresh_token_limiter,
                                            resend_verify_email_limiter,
                                            verify_email_limiter,
                                            forgot_password_email_limiter,
                                            reset_password_limiter,
                                            upload_limiter,
                                            create_post_limiter,
                                            get_posts_limiter,
                                            react_to_post_limiter,
                                            get_tags_limiter,
                                            find_posts_limiter,
                                            find_tags_limiter,
                                            find_posts_with_tag_limiter,
                                            delete_post_limiter,
                                            update_post_limiter,
                                            get_post_limiter,
                                            create_comment_limiter,
                                            get_root_comments_limiter,
                                            get_root_replies_limiter,
                                            react_to_comment_limiter,
                                            delete_comment_limiter,
                                            update_comment_limiter)



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
        
        
async def disable_rate_limiter():
    pass


@pytest.fixture
def test_app():
    app = create_app(with_lifespan=False)

    app.dependency_overrides[register_rate_limiter] = disable_rate_limiter
    app.dependency_overrides[get_me_limiter] = disable_rate_limiter
    app.dependency_overrides[get_users_limiter] = disable_rate_limiter
    app.dependency_overrides[find_users_limiter] = disable_rate_limiter
    app.dependency_overrides[get_user_profile_limiter] = disable_rate_limiter
    app.dependency_overrides[get_user_posts_limiter] = disable_rate_limiter
    app.dependency_overrides[delete_user_limiter] = disable_rate_limiter
    app.dependency_overrides[update_user_limiter] = disable_rate_limiter
    
    app.dependency_overrides[login_limiter] = disable_rate_limiter
    app.dependency_overrides[logout_limiter] = disable_rate_limiter
    app.dependency_overrides[refresh_token_limiter] = disable_rate_limiter
    app.dependency_overrides[resend_verify_email_limiter] = disable_rate_limiter
    app.dependency_overrides[verify_email_limiter] = disable_rate_limiter
    app.dependency_overrides[forgot_password_email_limiter] = disable_rate_limiter
    app.dependency_overrides[reset_password_limiter] = disable_rate_limiter
    
    app.dependency_overrides[upload_limiter] = disable_rate_limiter
    
    app.dependency_overrides[create_post_limiter] = disable_rate_limiter
    app.dependency_overrides[get_posts_limiter] = disable_rate_limiter
    app.dependency_overrides[react_to_post_limiter] = disable_rate_limiter
    app.dependency_overrides[get_tags_limiter] = disable_rate_limiter
    app.dependency_overrides[find_posts_limiter] = disable_rate_limiter
    app.dependency_overrides[find_tags_limiter] = disable_rate_limiter
    app.dependency_overrides[find_posts_with_tag_limiter] = disable_rate_limiter
    app.dependency_overrides[delete_post_limiter] = disable_rate_limiter
    app.dependency_overrides[update_post_limiter] = disable_rate_limiter
    app.dependency_overrides[get_post_limiter] = disable_rate_limiter
    
    app.dependency_overrides[create_comment_limiter] = disable_rate_limiter
    app.dependency_overrides[get_root_comments_limiter] = disable_rate_limiter
    app.dependency_overrides[get_root_replies_limiter] = disable_rate_limiter
    app.dependency_overrides[react_to_comment_limiter] = disable_rate_limiter
    app.dependency_overrides[delete_comment_limiter] = disable_rate_limiter
    app.dependency_overrides[update_comment_limiter] = disable_rate_limiter
                                                                                                       

    yield app

    app.dependency_overrides.clear()
        
        
@pytest_asyncio.fixture
async def async_client(test_app):

    async with AsyncClient(transport=ASGITransport(app=test_app),
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
