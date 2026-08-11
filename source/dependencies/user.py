from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from source.database.db_connect import get_db
from source.services.user import UserService
from source.repositories.user import UserRepository
from source.core.logger import default_logger
from source.cache.redis_backend import redis_backend


def get_user_service(db_session: AsyncSession = Depends(get_db)) -> UserService:
    default_logger.debug("Getting user service Dependency: Creating user repository")
    user_repo = UserRepository(db_session)
    default_logger.debug("Getting user service Dependency: Creating user service")
    return UserService(user_repo, redis_backend)