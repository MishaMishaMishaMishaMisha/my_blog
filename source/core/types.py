from typing import Annotated
from enum import Enum
from fastapi import Path, Query
from uuid import UUID
from pathlib import Path as PathDir
from datetime import timedelta


# язык на котором в основном будут посты. нужен для быстрого поиска
post_language = 'english'

# ограничение длины строк
str_256 = Annotated[str, 256]
str_120 = Annotated[str, 120]
str_50 = Annotated[str, 50]
str_20 = Annotated[str, 20]

# тип id для динамических параметров в эндопоинтах
POST_ID_TYPE = Annotated[UUID, Path(..., title="id of post")]
USER_ID_TYPE = Annotated[UUID, Path(..., title="id of user")]
COMMENT_ID_TYPE = Annotated[UUID, Path(..., title="id of comment")]

# необязательные параметры в эндпоинтах для получения списка моделей
LIMIT_QUERY = Annotated[int, Query(title="amount of elements", ge=1, le=100)]
OFFSET_QUERY = Annotated[int, Query(title="Offset", ge=0)]



# url для хранилища файлов
BASE_DIR = PathDir(__file__).resolve().parent.parent.parent
STORAGE_PATH = BASE_DIR / "uploads"

MAX_UPLOADED_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

MAX_TIME_EXISTING_TEMP_FILE = timedelta(days=1)

MAX_ATTACHMENTS_IN_POST = 50
MAX_ATTACHMENTS_IN_COMMENT = 1

ALLOWED_FILE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "video/mp4",
    "video/webm"
}


# enums типы
class RoleEnum(str, Enum):
    ADMIN = "admin"
    USER = "user"

class TokenTypeEnum(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"
    
class TypeReactionEnum(str, Enum):
    LIKE = "like"
    DISLIKE = "dislike"
    FIRE = "fire"
    SHIT = "shit"
    LAUGH = "laugh"
    
class FileTypeEnum(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    
class PostsSortEnum(str, Enum):
    NEW = "new"
    POPULAR = "popular"

class PeriodEnum(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    ALL_TIME = "all_time"



# необязательные параметры в эндпоинтах для сортировки списка постов
SORT_QUERY = Annotated[PostsSortEnum, Query(title="Sorting type")]
PERIOD_QUERY = Annotated[PeriodEnum, Query(title="Popularity period")]