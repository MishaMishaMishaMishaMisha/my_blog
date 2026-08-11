from abc import ABC, abstractmethod
from dataclasses import dataclass
from source.core.types import FileTypeEnum
from fastapi import UploadFile


@dataclass(slots=True, frozen=True)
class SavedFile:
    filename: str
    size: int
    mime_type: str
    file_type: FileTypeEnum
    

class BaseStorage(ABC):
        
    @abstractmethod
    def list_files(self) -> list[str]:
        pass

    @abstractmethod
    def save(self, file: UploadFile) -> SavedFile:
        pass

    @abstractmethod
    def delete(self, filename: str) -> None:
        pass
