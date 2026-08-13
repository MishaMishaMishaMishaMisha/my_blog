from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import text, ForeignKey, DateTime
from source.models.base import BaseORMModel
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint
from source.core.types import MAX_UPLOADED_FILE_SIZE, FileTypeEnum, STORAGE_PATH
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import UUID as SQLAlchemy_UUID
from pathlib import Path as PathDir

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

    filename: Mapped[str] # имя с присвоенным id. не url. пример 1234_cat.png
    
    # video or image
    file_type: Mapped[FileTypeEnum] = mapped_column(SQLEnum(FileTypeEnum, native_enum=False))
    
    # content type. for example "image/png" or "video/mp4"
    mime_type: Mapped[str]
    
    size: Mapped[int]
    
    uploaded_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            server_default=text("now()"))
    
    # сразу после загрузки файл становится временным
    # когда будет готов пост или комментарий то поле меняется на False
    # временные файлы будут удалены через некоторое время
    is_temporary: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    
    
    # пост в котором может находится этот файл
    post: Mapped["PostModel"] = relationship(back_populates="attachments")
    
    # комментарий в котором может находится этот файл
    comment: Mapped["CommentModel"] = relationship(back_populates="attachments")
    
    
    
    @property
    def url(self) -> str:
        return str(STORAGE_PATH / PathDir(self.filename))
    
    __table_args__ = (
        CheckConstraint(f"size <= {MAX_UPLOADED_FILE_SIZE}", name="ck_file_size"),
        # файл не может быть одновременно быть в посте и в комментарии
        #CheckConstraint("post_id IS NULL OR comment_id IS NULL", name="ck_attachment_single_owner")
    )
