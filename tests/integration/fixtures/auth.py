import pytest_asyncio
from source.core.security import (
    create_access_token,
    create_refresh_token,
)
from source.core.types import RoleEnum


# создает подтвержденного пользователя в таблице и генерирует для него токены
@pytest_asyncio.fixture
async def authenticated_user(users_factory):

    user = (await users_factory(is_verified=True))[0]

    return {
        "user": user,
        "access_token": create_access_token(
            user.id,
            RoleEnum(user.role),
        ),
        "refresh_token": create_refresh_token(
            user.id,
        ),
    }
    
# неподтвержденный пользователь
@pytest_asyncio.fixture
async def authenticated_notVerified_user(users_factory):

    user = (await users_factory())[0]

    return {
        "user": user,
        "access_token": create_access_token(
            user.id,
            RoleEnum(user.role),
        ),
        "refresh_token": create_refresh_token(
            user.id,
        ),
    }

# admin    
@pytest_asyncio.fixture
async def authenticated_admin(users_factory):

    user = (await users_factory(role=RoleEnum.ADMIN, is_verified=True))[0]

    return {
        "user": user,
        "access_token": create_access_token(
            user.id,
            RoleEnum(user.role),
        ),
        "refresh_token": create_refresh_token(
            user.id,
        ),
    }



# создает count пользователей в таблице и создает для каждого токены
@pytest_asyncio.fixture
async def authenticated_users(users_factory):

    async def factory(
        count: int = 1,
        **kwargs,
    ):

        users = await users_factory(
            count=count,
            **kwargs,
        )

        return [
            {
                "user": user,
                "access_token": create_access_token(
                    user.id,
                    RoleEnum(user.role),
                ),
                "refresh_token": create_refresh_token(
                    user.id,
                ),
            }
            for user in users
        ]

    return factory