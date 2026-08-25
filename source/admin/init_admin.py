import os

from sqlalchemy.ext.asyncio import (AsyncSession,
                                    async_sessionmaker,
                                    create_async_engine)
from sqlalchemy import select

from source.models.user import UserModel
from source.core.types import RoleEnum  
from source.core.security import hash_password
from source.core.config import settings
from source.core.logger import default_logger


async def create_first_admin() -> None:
    
    admin_username = os.getenv("ADMIN_USERNAME", "admin_username")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "supersecretpassword")
    
    default_logger.info(f"Creating admin <{admin_email}>. Checking if exists")
    
    # создаем локальное подключение к бд
    engine = create_async_engine(settings.db.url_asyncpg)
    session_factory = async_sessionmaker(bind=engine,
                                         class_=AsyncSession,
                                         expire_on_commit=False)
            
    async with session_factory() as session:

        # Проверяем, существует ли уже админ
        result = await session.execute(select(UserModel)
                                    .where(UserModel.email==admin_email))
        admin_exists = result.scalar_one_or_none()

        if not admin_exists:
            admin_model = UserModel(username=admin_username,
                                email=admin_email,
                                password_hash=hash_password(admin_password),
                                role=RoleEnum.ADMIN,
                                is_verified=True,
                                is_active=True)

            session.add(admin_model)
            await session.commit()
            
            default_logger.info(f"Creating admin <{admin_email}>. Created")
        else:
            default_logger.info(f"Creating admin <{admin_email}>. Already exists")

