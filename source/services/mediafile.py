from source.models.attachment_media import AttachmentMediaModel
from source.core.logger import default_logger
from source.repositories.mediafile import MediaFileRepository
from uuid import UUID
from fastapi import UploadFile
from source.core.types import ALLOWED_FILE_TYPES
from source.core.exceptions import NotAllowedFileTypeException, FileWritingException, FileAddingException
from source.services.storage.localStorage import LocalStorage
from source.schemas.attachment import AttachmentDTO



class MediaFileService:

    def __init__(self, mediafile_repo: MediaFileRepository, storage: LocalStorage):
        
        self.mediafile_repo = mediafile_repo
        self.storage = storage

    async def add_file(self, file: UploadFile, user_id: UUID) -> AttachmentDTO:

        if file.content_type not in ALLOWED_FILE_TYPES:
            raise NotAllowedFileTypeException("File type is unsupperted")

        try:
            saved_file = self.storage.save(file)
            default_logger.info("Uploading file: file saved in storage")

            model = AttachmentMediaModel(
                user_id=user_id,
                filename=saved_file.filename,
                size=saved_file.size,
                mime_type=saved_file.mime_type,
                file_type=saved_file.file_type)

            await self.mediafile_repo.add_file(model)
            
            return AttachmentDTO.model_validate(model)
            #return model

        except FileWritingException as e:

            self.storage.delete(saved_file.filename)

            raise FileAddingException(str(e))
        
    async def delete_file(self, file_id: UUID):
        deleted_filename = await self.mediafile_repo.delete_file(file_id)
        
        default_logger.info("Deleting temp files: deleting file from storage")
        self.storage.delete(deleted_filename)
        
    async def delete_temp_files(self):
        
        default_logger.info("Deleting temp files: checking temp files")
        
        deleted_temp_filenames = await self.mediafile_repo.delete_temp_files()
        
        if deleted_temp_filenames:
            default_logger.info(f"Deleting temp files: found {len(self.delete_temp_files)} temp files")
            
            for fname in deleted_temp_filenames:
                self.storage.delete(fname)
            
            default_logger.info("Deleting temp files: temp files deleted")
        else:
            default_logger.info("Deleting temp files: temp files not found")
        

    async def sync_storage_and_db(self):
        default_logger.info("Sync storage: started")

        # Получаем имена файлов из БД
        db_files = await self.mediafile_repo.get_files()

        # Получаем имена файлов из хранилища
        storage_files = set(self.storage.list_files())

        # Есть в storage, но нет в БД
        orphan_files = storage_files - db_files

        # Есть в БД, но нет в storage
        missing_files = db_files - storage_files

        if orphan_files:
            default_logger.info(
                "Sync storage: deleting %d orphan files",
                len(orphan_files),
            )

            for filename in orphan_files:
                self.storage.delete(filename)

        if missing_files:
            default_logger.info(
                "Sync storage: deleting %d orphan records",
                len(missing_files),
            )

            await self.mediafile_repo.delete_files(missing_files)

        default_logger.info(
            "Sync storage: finished (deleted files=%d, deleted records=%d)",
            len(orphan_files),
            len(missing_files),
        )