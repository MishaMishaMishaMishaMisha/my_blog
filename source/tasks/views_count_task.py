from uuid import UUID

from celery import signals
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from source.cache.redis_backend import RedisBackend
from source.celery_app.celery_app import app
from source.core.config import settings
from source.repositories.post import PostRepository
from source.core.logger import default_logger
import asyncio


@app.task
def update_views_count() -> None:
    asyncio.run(update_views_count_async_task())

async def update_views_count_async_task() -> None:
    
    default_logger.info("Celery task. Update views count. Start (new version)")
    
    redis = RedisBackend()

    # переименовываем ключ
    processing_key = "post_views_processing"

    try:
        await redis.renameKey("post_views", processing_key)
    except Exception:
        default_logger.debug("Celery. Key post_views is not set")
        return
    
    # создаем новый движок и сессию для подключения к бд
    # так как задача запускается в номов event loop
    engine = create_async_engine(settings.db.url_asyncpg)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        # получаем все views_count и обновляем в базе
        views = await redis.hgetall(processing_key)

        updates = [
            (UUID(post_id), int(count))
            for post_id, count in views.items()
        ]

        default_logger.info("Celery task. Update views count. executing query")
            
        async with session_factory() as session:
            repo = PostRepository(session)
            await repo.bulk_increment_views(updates)
            await repo.make_commit()
            
        default_logger.info("Celery task. Update views count. executing query done")

        # удаляем ключ
        await redis.delete(processing_key)
        
        default_logger.debug("Updating views count: Done")

    except Exception as e:
        default_logger.error(f"Celery. Error in views_count_task. {e}")