from uuid import UUID

from celery import signals
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from source.celery_app.celery_app import app
from source.core.config import settings
from source.services.mediafile import MediaFileService
from source.repositories.mediafile import MediaFileRepository
from source.services.storage.localStorage import LocalStorage
from source.core.types import STORAGE_PATH
from source.core.logger import default_logger
import asyncio


@app.task
def delete_temp_files() -> None:
    asyncio.run(delete_temp_files_async_task())
    
@app.task
def sync_Files_in_Storage_and_in_DB() -> None:
    asyncio.run(sync_Files_in_Storage_and_in_DB_async_task())
    

async def delete_temp_files_async_task() -> None:
    
    default_logger.info("Celery task. Delete temp files. Start")
    
    # создаем новый движок и сессию для подключения к бд
    # так как задача запускается в номов event loop
    engine = create_async_engine(settings.db.url_asyncpg)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
            
        async with session_factory() as session:
            repo = MediaFileRepository(session)
            service = MediaFileService(repo, LocalStorage(STORAGE_PATH))
            
            await service.delete_temp_files()
            
        default_logger.info("Celery task. Delete temp files. Done")


    except Exception as e:
        default_logger.error(f"Celery task. Error while Deleting temp files. {e}")
        


async def sync_Files_in_Storage_and_in_DB_async_task() -> None:
    
    default_logger.info("Celery task. Sync files. Start")
    
    # создаем новый движок и сессию для подключения к бд
    # так как задача запускается в номов event loop
    engine = create_async_engine(settings.db.url_asyncpg)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
            
        async with session_factory() as session:
            repo = MediaFileRepository(session)
            service = MediaFileService(repo, LocalStorage(STORAGE_PATH))
            
            await service.sync_storage_and_db()
            
        default_logger.info("Celery task. Sync files. Done")


    except Exception as e:
        default_logger.error(f"Celery task. Error while sync files. {e}")