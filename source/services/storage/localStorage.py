from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4
from fastapi import UploadFile
from source.core.exceptions import FileWritingException
from source.core.logger import default_logger
from source.core.types import FileTypeEnum
from source.services.storage.baseStorage import BaseStorage, SavedFile


    

class LocalStorage(BaseStorage):

    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        
    def list_files(self) -> list[str]:
        return [path.name for path in self.upload_dir.iterdir() if path.is_file()]

    def save(self, file: UploadFile) -> SavedFile:

        filename = f"{uuid4()}_{file.filename}"
        path = self.upload_dir / filename
        mimeType = file.content_type
        if not mimeType:
            raise FileWritingException("Content type is missing")
        fileType = FileTypeEnum(mimeType[:mimeType.find("/")])
        
        default_logger.info(f"Uploading file: filename={filename}, path={path}")

        try:
            with open(path, "wb") as buffer:
                copyfileobj(file.file, buffer)

        except OSError as e:
            # если запись оборвалась — удалить частично записанный файл
            if path.exists():
                path.unlink()

            default_logger.error(f"Uploading file: file writing error")
            raise FileWritingException("Failed to save file") from e

        return SavedFile(
            filename=filename,
            size=path.stat().st_size,
            mime_type=mimeType,
            file_type=fileType
        )

    def delete(self, filename: str) -> None:

        path = self.upload_dir / filename
        default_logger.debug(f"Deleting file: try to delete from storage. File: {path}")
        try:
            if path.exists():
                path.unlink()

        except OSError:
            default_logger.error("Error while deleting file from disk")