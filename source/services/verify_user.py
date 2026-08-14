from uuid import UUID

from source.repositories.user import UserRepository
from source.models.user import UserModel
from source.cache.redis_backend import RedisBackend
from source.core.logger import default_logger
from source.core.exceptions import (InvalidTokenException, 
                                    UserAlreadyCreatedVerifyLink, 
                                    UserAlreadyCreatedResetpasswordLink)
from source.core.security import (create_verify_email_token, 
                                  create_reset_password_token, 
                                  decode_token, 
                                  hash_password,
                                  get_token_expire_time_seconds_left)
from source.core.types import TokenTypeEnum
from source.core.config import settings


class VerifyUserService:
    
    def __init__(self, user_repo: UserRepository, redis_cache: RedisBackend):
        self.user_repo = user_repo
        self.redis_cache = redis_cache
    
    async def create_verify_link(self, user_id: UUID) -> str:
        
        is_link_created = await self.redis_cache.get(key=f"created-verify-link:user:{user_id}")
        if is_link_created:
            raise UserAlreadyCreatedVerifyLink("You alreay created verify link. Try later")
        
        default_logger.debug("Creating verify link")
        token = create_verify_email_token(user_id)
        verify_link = "http://localhost:5173/auth/verify-email?token=" + token
        
        # добавим в кеш запись о том что ссылка создана
        await self.redis_cache.set(key=f"created-verify-link:user:{user_id}",
                                   value=1, # значение не важно. главное наличие ключа
                                   ttl_seconds=settings.jwt.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS * 3600)
        
        return verify_link
    
    async def verify_email(self, token: str) -> None:
        
        default_logger.debug("Verifying email")
        payload = decode_token(token)
        if not payload or payload.get("type") != TokenTypeEnum.VERIFY_EMAIL:
            default_logger.error("Verifying email: Error. Invalid or expired token")
            raise InvalidTokenException("Invalid or expired token")
        
        # проверяем пользовался ли пользователь этой ссылкой
        is_token_in_blacklist = await self.redis_cache.get(
                        key=f"verify-user-token:{payload.get("jti")}")
        if is_token_in_blacklist:
            default_logger.error("Verifying email: Error. Token in blacklist")
            raise InvalidTokenException("Token in blacklist")
            
        
        user_id = UUID(payload["sub"])
        user = await self.user_repo.verify_user(user_id)
        
        # добавим токен в блеклист
        time_left = get_token_expire_time_seconds_left(payload)
        if not time_left:
            default_logger.error("Verifying email: Error. Token havenot exp key")
            raise InvalidTokenException("Token havenot exp key")
        
        await self.redis_cache.set(key=f"verify-user-token:{payload.get("jti")}",
                                   value=1, # значение не важно. главное наличие ключа
                                   ttl_seconds=time_left)
        
        # удалить профиль из кеша
        await self.redis_cache.delete(key=f"user-profile:{user.username}")
        
    async def create_resetPassword_link(self, user_id: UUID) -> str:
        
        is_link_created = await self.redis_cache.get(key=f"created-reset-password-link:user:{user_id}")
        if is_link_created:
            raise UserAlreadyCreatedResetpasswordLink("You already created link. Try later")
        
        default_logger.debug("Creating reset password link")
        token = create_reset_password_token(user_id)
        reset_link = "http://localhost:5173/reset-password?token=" + token
        
        # добавим в кеш запись о том что ссылка создана
        await self.redis_cache.set(key=f"created-reset-password-link:user:{user_id}",
                                   value=1, # значение не важно. главное наличие ключа
                                   ttl_seconds=settings.jwt.RESET_PASSWORD_TOKEN_EXPIRE_MINUTES * 60)
        
        return reset_link

    async def reset_password(self, token: str, new_password: str) -> None:    
        
        default_logger.debug("Checking reset password token")
        payload = decode_token(token)
        if not payload or payload.get("type") != TokenTypeEnum.RESET_PASSWORD:
            default_logger.error("Checking reset password token: Error. Invalid or expired token")
            raise InvalidTokenException("Invalid or expired token")
        
        # проверяем пользовался ли юзер этой ссылкой
        is_token_in_blacklist = await self.redis_cache.get(
                        key=f"reset-password-token:{payload.get("jti")}")
        if is_token_in_blacklist:
            default_logger.error("Checking reset password token: Error. Token in blacklist")
            raise InvalidTokenException("Token in blacklist")
        
        user_id = UUID(payload["sub"])
        hashed_password = hash_password(new_password)
        await self.user_repo.reset_password(user_id, hashed_password)
        
        # добавить токен в блеклист
        time_left = get_token_expire_time_seconds_left(payload)
        if not time_left:
            default_logger.error("Checking reset password token: Error. Token havenot exp key")
            raise InvalidTokenException("Token havenot exp key")
        
        await self.redis_cache.set(key=f"reset-password-token:{payload.get("jti")}",
                                   value=1, # значение не важно. главное наличие ключа
                                   ttl_seconds=time_left)
        
    async def find_user_by_email(self, email: str) -> UserModel | None:
        return await self.user_repo.get_user_by(email=email)