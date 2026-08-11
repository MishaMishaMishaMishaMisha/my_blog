from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from source.core.exceptions import FileNotFoundException
from source.core.logger import default_logger
from typing import Sequence
from uuid import UUID
from source.models.attachment_media import AttachmentMediaModel
from source.core.types import MAX_TIME_EXISTING_TEMP_FILE


class MediaFileRepository:
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        
    async def make_commit(self):
        await self.db_session.commit()
        
    async def make_rollback(self) -> None:
        await self.db_session.rollback()
        
    def add_file(self, mediafile: AttachmentMediaModel) -> None:
        self.db_session.add(mediafile)
    
    async def delete_file(self, file_id: UUID) -> str:
        query = (delete(AttachmentMediaModel)
                 .where(AttachmentMediaModel.id==file_id)
                 .returning(AttachmentMediaModel.filename))
        result = await self.db_session.execute(query)
        deleted_filename = result.scalar_one_or_none()
        if deleted_filename is None:
            default_logger.error(f"Deleting file. Error. File not found")
            raise FileNotFoundException("File not found")
        #await self.db_session.commit()
        default_logger.debug("Deleting file: file info deleted from db")
        return deleted_filename
    
    async def delete_files(self, filenames: set[str]) -> None:
        query = (delete(AttachmentMediaModel)
                 .where(AttachmentMediaModel.filename.in_(filenames)))
        await self.db_session.execute(query)
    
    async def delete_temp_files(self) -> Sequence[str]:
        query = (delete(AttachmentMediaModel).where(and_(
            AttachmentMediaModel.post_id.is_(None),
            AttachmentMediaModel.comment_id.is_(None),
            AttachmentMediaModel.is_temporary.is_(True),
            AttachmentMediaModel.uploaded_at < func.now() - MAX_TIME_EXISTING_TEMP_FILE)
        ).returning(AttachmentMediaModel.filename))
        
        res = await self.db_session.execute(query)
        deleted_temp_filenames = res.scalars().all()
        return deleted_temp_filenames
        
    async def get_files(self) -> set[str]:
        #res =  await self.db_session.execute(select(AttachmentMediaModel.filename))
        #return res.scalars().all()
        
        # используем stream чтобы не выгружать за раз все файлы
        db_files = set()
        stream = await self.db_session.stream_scalars(select(AttachmentMediaModel.filename))
        async for filename in stream:
            db_files.add(filename)
        return db_files