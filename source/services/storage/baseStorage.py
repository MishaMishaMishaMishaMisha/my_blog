from abc import ABC, abstractmethod
from dataclasses import dataclass
from fastapi import UploadFile

from source.core.types import FileTypeEnum


# slots=True нельзя будет добавить новые атрибуты
# frozen=True нельзя изменить поля у экземпляра класса
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
