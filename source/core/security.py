import jwt

from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from pydantic import ValidationError
from uuid import UUID, uuid4
from typing import Any

from source.core.config import settings
from source.core.types import RoleEnum, TokenTypeEnum
from source.core.logger import default_logger


# configure passlib
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    default_logger.debug(f"Hashing password...")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    default_logger.debug(f"Verifying passord...")
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt_token(data: dict, expires_delta: timedelta) -> str:
    default_logger.debug("Creating jwt token")
    data_to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    data_to_encode.update({"exp": expire}) # добавляем exp
    return jwt.encode(data_to_encode, settings.jwt.SECRET_KEY, algorithm=settings.jwt.ALGORITHM)
    

def create_access_token(user_id: UUID, role: RoleEnum) -> str:
    payload = {"sub": str(user_id), "role": role, "type": TokenTypeEnum.ACCESS}
    return create_jwt_token(payload, timedelta(minutes=settings.jwt.ACCESS_TOKEN_EXPIRE_MINUTES))

def create_refresh_token(user_id: UUID) -> str:
    payload = {"sub": str(user_id), "type": TokenTypeEnum.REFRESH}
    return create_jwt_token(payload, timedelta(days=settings.jwt.REFRESH_TOKEN_EXPIRE_DAYS))

def create_verify_email_token(user_id: UUID) -> str:
    payload = {"jti": str(uuid4()), # Уникальный ID токена
               "sub": str(user_id), 
               "type": TokenTypeEnum.VERIFY_EMAIL}
    return create_jwt_token(payload, timedelta(hours=settings.jwt.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS))

def create_reset_password_token(user_id: UUID) -> str:
    payload = {"jti": str(uuid4()), # Уникальный ID токена
               "sub": str(user_id), 
               "type": TokenTypeEnum.RESET_PASSWORD}
    return create_jwt_token(payload, timedelta(hours=settings.jwt.RESET_PASSWORD_TOKEN_EXPIRE_MINUTES))

def decode_token(token: str) -> dict | None:
    try:
        default_logger.debug("Decoding token: TRYING")
        payload = jwt.decode(token, settings.jwt.SECRET_KEY, algorithms=settings.jwt.ALGORITHM)
        default_logger.debug("Decoding token: FINISHED")
        return payload
    except jwt.PyJWTError:
        default_logger.error("Decoding token: ERROR. Token has expired")
    except ValidationError:
        default_logger.error("Decoding token: ERROR. Validation error")

    return None


def get_token_expire_time_seconds_left(payload: dict[str, Any]) -> int | None:
    if not payload or not payload.get("exp"):
        return None
    
    exp_timestamp = payload.get("exp")
    now_timestamp = int(datetime.now(timezone.utc).timestamp())
    time_left = exp_timestamp - now_timestamp
    return time_left


        
if __name__ == "__main__":
    print("security file")
    