from source.core.logger import default_logger
from source.core.exceptions import InvalidTokenException
from source.core.security import create_verify_email_token, create_reset_password_token, decode_token, hash_password
from source.core.types import TokenTypeEnum
from uuid import UUID
from source.repositories.user import UserRepository
from source.models.user import UserModel


class VerifyUserService:
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    def create_verify_link(self, user_id: UUID) -> str:
        default_logger.debug("Creating verify link")
        token = create_verify_email_token(user_id)
        verify_link = "http://127.0.0.1:8000/auth/verify-email?token=" + token
        return verify_link
    
    async def verify_email(self, token: str) -> None:
        
        default_logger.debug("Verifying email")
        payload = decode_token(token)
        if not payload or payload.get("type") != TokenTypeEnum.VERIFY_EMAIL:
            default_logger.error("Verifying email: Error. Invalid or expired token")
            raise InvalidTokenException("Invalid or expired token")
        
        user_id = UUID(payload["sub"])
        await self.user_repo.verify_user(user_id)
        
    def create_resetPassword_link(self, user_id: UUID) -> str:
        default_logger.debug("Creating reset password link")
        token = create_reset_password_token(user_id)
        reset_link = "http://127.0.0.1:8000/reset-password?token=" + token
        return reset_link
        # из этой ссылки фронтенд извлечет token 
        # и просто отправит клиента на страницу с вводом нового пароля
    
    async def reset_password(self, token: str, new_password: str) -> None:    
        default_logger.debug("Checking reset password token")
        payload = decode_token(token)
        if not payload or payload.get("type") != TokenTypeEnum.RESET_PASSWORD:
            default_logger.error("Checking reset password token: Error. Invalid or expired token")
            raise InvalidTokenException("Invalid or expired token")
        
        user_id = UUID(payload["sub"])
        hashed_password = hash_password(new_password)
        await self.user_repo.reset_password(user_id, hashed_password)
        
    async def find_user_by_email(self, email: str) -> UserModel | None:
        return await self.user_repo.get_user_by(email=email)