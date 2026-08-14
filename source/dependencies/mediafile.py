from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from source.database.db_connect import get_db
from source.services.mediafile import MediaFileService
from source.repositories.mediafile import MediaFileRepository
from source.core.logger import default_logger
from source.services.storage.localStorage import LocalStorage
from source.core.types import STORAGE_PATH


def get_mediafile_service(db_session: AsyncSession = Depends(get_db)) -> MediaFileService:
    default_logger.debug("Getting upload service Dependency: ...")
    storage = LocalStorage(STORAGE_PATH)
    mediafile_repo = MediaFileRepository(db_session)
    return MediaFileService(mediafile_repo, storage)