from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from source.database.db_connect import get_db
from source.services.comment import CommentService
from source.repositories.comment import CommentRepository
from source.core.logger import default_logger
from source.services.storage.localStorage import LocalStorage
from source.core.types import STORAGE_PATH
from source.cache.redis_backend import RedisBackend


def get_comment_service(db_session: AsyncSession = Depends(get_db)) -> CommentService:
    default_logger.debug("Getting comment service Dependency: Creating comment repository")
    comment_repo = CommentRepository(db_session, LocalStorage(STORAGE_PATH))
    default_logger.debug("Getting comment service Dependency: Creating comment service")
    return CommentService(comment_repo, RedisBackend())