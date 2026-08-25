from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from uuid import UUID

from source.core.types import RoleEnum
from source.database.db_connect import async_session_factory
from source.services.auth import AuthService
from source.repositories.user import UserRepository


class AdminAuth(AuthenticationBackend):
    
    def __init__(self, secret_key: str):
        super().__init__(secret_key)
    
    async def login(self, request: Request) -> bool:
        form = await request.form()

        username = form.get("username")
        password = form.get("password")
        
        async with async_session_factory() as db_session:
            auth_service = AuthService(UserRepository(db_session))
            user = await auth_service.authenticate_admin(login=username,
                                                         password=password)
        
        if not user:
            return False

        request.session.update({"user_id": str(user.id)})

        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("user_id")

        if user_id is None:
            return False

        try:
            user_id = UUID(user_id)
        except ValueError:
            return False

        async with async_session_factory() as db_session:
            auth_service = AuthService(UserRepository(db_session))
            user = await auth_service.get_user_by_id(user_id)

        if (user is None) or (not user.is_active):
            return False

        if user.role != RoleEnum.ADMIN:
            return False

        return True
    