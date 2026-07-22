from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from source.core.config import settings
from source.core.logger import default_logger

default_logger.debug(f"CREATING DATA BASE <{settings.db.NAME}>")

async_engine = create_async_engine(url=settings.db.url_asyncpg)

async_session_factory = async_sessionmaker(bind=async_engine, expire_on_commit=False)
# expire_on_commit делает так что после commit, SQLAlchemy считает объект устаревшим
# при повтороном обращении к нему, будет сделан новый запрос
# в асинхнронном режиме могут быть с этим проблемы поэтому отменяем это, сделав его False

async def get_db():
    async with async_session_factory() as session:
        default_logger.debug("Getting async session")
        yield session