from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from source.database.db_connect import get_db
from source.services.post import PostService
from source.repositories.post import PostRepository
from source.core.logger import default_logger
from source.services.storage.localStorage import LocalStorage
from source.core.types import STORAGE_PATH
from source.cache.redis_backend import redis_backend


def get_post_service(db_session: AsyncSession = Depends(get_db)) -> PostService:
    default_logger.debug("Getting post service Dependency: Creating post repository")
    post_repo = PostRepository(db_session, LocalStorage(STORAGE_PATH))
    default_logger.debug("Getting post service Dependency: Creating post service")
    return PostService(post_repo, redis_backend)

