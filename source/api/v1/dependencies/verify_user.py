from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from source.database.db_connect import get_db
from source.services.verify_user import VerifyUserService
from source.repositories.user import UserRepository
from source.core.logger import default_logger
from source.cache.redis_backend import redis_backend



def get_verify_user_service(db_session: AsyncSession = Depends(get_db)) -> VerifyUserService:
    default_logger.debug("Getting verify user service Dependency")
    user_repo = UserRepository(db_session)
    return VerifyUserService(user_repo, redis_backend)