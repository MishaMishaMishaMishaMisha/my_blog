from uuid import UUID
from datetime import datetime

from source.models.user import UserModel
from source.repositories.user import UserRepository
from source.api.v1.schemas.token import Token
from source.core.exceptions import (InvalidCredentialsException, 
                                    InvalidTokenException,
                                    UserNotFoundException)
from source.core.logger import default_logger
from source.core.types import TokenTypeEnum, RoleEnum
from source.core.security import (verify_password, 
                                  create_access_token, 
                                  create_refresh_token, 
                                  decode_token)


class AuthService:
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        
    async def authenticate_user(self, login: str, password: str) -> Token:
        default_logger.debug("Authenication user: Checking credentials")

        if "@" in login:
            user = await self.user_repo.get_user_by(email=login)
        else:
            user = await self.user_repo.get_user_by(username=login)
        
        if not user:
            raise InvalidCredentialsException("Invalid email or username")
        
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsException("Incorrect password")
        
        if not user.is_active:
            raise InvalidCredentialsException("User is unactive")
        
        user.last_login = datetime.now()
        user.last_seen = user.last_login
        await self.user_repo.make_commit()
        
        default_logger.debug("Authenication user: Creating token")
        return Token(access_token=create_access_token(user.id, user.role),
                     refresh_token=create_refresh_token(user.id),
                     token_type="bearer")
    
    async def update_refresh_token(self, token: str) -> Token:
        default_logger.debug("Updating refresh token: Decoding token")
        payload = decode_token(token)
        if not payload or payload.get("type") != TokenTypeEnum.REFRESH:
            default_logger.error("Updating refresh token: Error. Invalid or expired token")
            raise InvalidTokenException("Invalid or expired token")
        
        default_logger.debug("Updating refresh token: Trying to find user by this token")
        user_id = UUID(payload["sub"])
        user = await self.user_repo.get_user_by(id=user_id)
        if not user:
            default_logger.error("Updating refresh token: Error. User not found")
            raise InvalidTokenException("User not found by id from token")
        
        if not user.is_active:
            default_logger.error("Updating refresh token: Error. User is unactive")
            raise InvalidTokenException("User is unactive")
        
        user.last_seen = datetime.now()
        await self.user_repo.make_commit()
        
        default_logger.debug("Updating refresh token: Creating new tokens")
        return Token(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id), # Ротация рефреш токена
            token_type="bearer")
        
        
    # для админки
    async def authenticate_admin(self, 
                                 login: str, 
                                 password: str) -> UserModel | None:
        
        default_logger.debug("Authenication admin: Checking credentials")

        if "@" in login:
            user = await self.user_repo.get_user_by(email=login)
        else:
            user = await self.user_repo.get_user_by(username=login)
        
        if (not user) or (not user.is_active) or (user.role != RoleEnum.ADMIN):
            default_logger.debug("Authenication admin: user dont have permission")
            return None
        
        if not verify_password(password, user.password_hash):
            default_logger.debug("Authenication admin: wrong password")
            return None
        
        default_logger.debug("Authenication admin: success")
        return user
    
    async def get_user_by_id(self, user_id: UUID) -> UserModel | None:

        try:
            default_logger.debug("Getting user by id: trying")
            user = await self.user_repo.get_user(user_id) 
            return user
        
        except UserNotFoundException:
            default_logger.debug("Getting user by id: user not found")
            return None