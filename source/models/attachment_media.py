import uuid

from sqlalchemy import text, ForeignKey, DateTime
from sqlalchemy import CheckConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import UUID as SQLAlchemy_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pathlib import Path as PathDir
from datetime import datetime

from source.models.base import BaseORMModel
from source.core.types import MAX_UPLOADED_FILE_SIZE, FileTypeEnum, STORAGE_PATH

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from source.models.post import PostModel
    from source.models.comment import CommentModel


class AttachmentMediaModel(BaseORMModel):
    __tablename__ = "attachment_medias"
    
    id: Mapped[uuid.UUID] = mapped_column(SQLAlchemy_UUID(as_uuid=True),
                                          primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    
    post_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"),
                                              index=True,
                                              nullable=True)
    
    comment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"),
                                              index=True,
                                              nullable=True)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), 
                                               index=True)

    # оригинальное имя файла. пример # cat.png
    orig_name: Mapped[str] = mapped_column(nullable=True)

    # имя с присвоенным id. не url. пример 1234_cat.png
    filename: Mapped[str]
    
    file_type: Mapped[FileTypeEnum] = mapped_column(SQLEnum(FileTypeEnum, native_enum=False))
    
    # пример "image/png", "video/mp4"
    mime_type: Mapped[str]
    
    size: Mapped[int]
    
    uploaded_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            server_default=text("now()"))
    
    # сразу после загрузки файл становится временным
    # когда будет готов пост или комментарий то поле меняется на False
    # временные файлы будут удалены через некоторое время
    is_temporary: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    
    
    # пост в котором находится этот файл
    post: Mapped["PostModel"] = relationship(back_populates="attachments")
    
    # комментарий в котором находится этот файл
    comment: Mapped["CommentModel"] = relationship(back_populates="attachments")
    
    
    @property
    def url(self) -> str:
        return str(STORAGE_PATH / PathDir(self.filename))
    
    __table_args__ = (
        CheckConstraint(f"size <= {MAX_UPLOADED_FILE_SIZE}", name="ck_file_size"),
    )
