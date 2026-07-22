from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from source.database.db_connect import get_db
from source.services.auth import AuthService
from source.repositories.user import UserRepository
from source.core.logger import default_logger
from fastapi.security import OAuth2PasswordBearer
from source.core.types import RoleEnum, TokenTypeEnum
from source.core.security import decode_token
from source.models.user import UserModel
from source.services.user import UserService
from source.dependencies.user import get_user_service
from source.core.exceptions import UserNotFoundException
from uuid import UUID



def get_auth_service(db_session: AsyncSession = Depends(get_db)) -> AuthService:
    default_logger.debug("Getting auth service Dependency: Creating user repository")
    user_repo = UserRepository(db_session)
    default_logger.debug("Getting auth service Dependency: Creating auth service")
    return AuthService(user_repo)


# эта штука автоматически будет доставать токен из заголовка authtorization: bearer
# параметр tokenUrl нужен только для удобной авторизации в swagger в документации
oauth2_schem = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_user_from_token(token: str = Depends(oauth2_schem),
                        user_service: UserService = Depends(get_user_service)) -> UserModel:
    
    # в dependency можно выбрасывать HttpException
    # так как это уже часть веба
    token_exception = HTTPException(
        status_code=401,
        detail="Could not validate token",
        headers={"WWW-Authenticate": "Bearer"})
    
    default_logger.debug(f"Getting user from token: Decoding token")
    payload = decode_token(token)
    if payload is None or payload["type"] != TokenTypeEnum.ACCESS:
        default_logger.error("Getting user from token: Error. Payload is empty or token is not access")
        raise token_exception
    
    default_logger.debug("Getting user from token: Getting user id in token")
    user_id = UUID(payload["sub"])
    if user_id is None:
        default_logger.error("Getting user from token: Error. Cant find user id in token")
        raise token_exception
    
    try:
        default_logger.debug("Getting user from token: Finding user in db")
        user = await user_service.get_user(user_id)
        
        # пользователь успешно получен. можно изменить last_seen
        await user_service.set_last_seen(user)
        
        return user
    except UserNotFoundException:
            default_logger.error("Getting user from token: Error. Cant find user in db")
            raise token_exception


# так как нам надо передать параметр
# то обычная функция не подойдет
# используем класс где 
# в init передаем параметр
# и переопределяем call чтобы 
# экземпляр класса можно было вызвать в Depends
class CheckUserRole:
    
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles
        
    async def __call__(self, user: UserModel = Depends(get_user_from_token)) -> UserModel:
        default_logger.debug("Checking user permissions")
        if user.role not in self.allowed_roles:
            default_logger.error("Error. User dont have permission")
            raise HTTPException(status_code=403, detail="You dont have enough permissions")
        default_logger.debug("Checking user permissions finished. Success")
        return user