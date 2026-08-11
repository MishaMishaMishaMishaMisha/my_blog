from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import text, ForeignKey, Text, DateTime
from source.models.base import BaseORMModel
from source.core.types import str_120, TypeReactionEnum
from datetime import datetime
import uuid
from sqlalchemy import UUID as SQLAlchemy_UUID
from typing import TYPE_CHECKING

# чтобы IDE не подчеркивала названия моделей в relationship
if TYPE_CHECKING:
    from source.models.user import UserModel
    from source.models.tag import TagModel
    from source.models.post_reaction import PostReactionModel
    from source.models.comment import CommentModel
    from source.models.attachment_media import AttachmentMediaModel


class PostModel(BaseORMModel):
    __tablename__ = "posts"
    
    id: Mapped[uuid.UUID] = mapped_column(SQLAlchemy_UUID(as_uuid=True),
                                          primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    title: Mapped[str_120] = mapped_column(index=True)
    
    # содержимое поста
    body: Mapped[str] = mapped_column(Text)
    
    # счетчик открывшых пост
    views_count: Mapped[int] = mapped_column(server_default=text("0"))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"))
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        server_onupdate=text("now()"))
    
    
    
    """Связи"""
    # список файлов использованных в посте
    attachments: Mapped[list["AttachmentMediaModel"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan"
    )

    # автор поста
    author: Mapped["UserModel"] = relationship(back_populates="posts")
    
    # список тегов у этого поста
    tags: Mapped[list["TagModel"]] = relationship(back_populates="posts_with_tag", 
                                                  secondary="post_tags")
    
    # список комментариев у этого поста
    comments: Mapped[list["CommentModel"]] = relationship(back_populates="post")

    # список реакций у этого поста оставленных пользователями
    # реакции достаем напрямую из PostReationModel
    # поэтому параметр secondary здесь не нужен 
    reactions_list: Mapped[list["PostReactionModel"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan")
    # cascade:
        # это аналог ondelete=""CASCADE" из бд но для связей в алхимии
        # all означает что при добавлении нового поста, алхимия автоматически добавит все реакции в бд
        # delete-orphan означает что при удалении реакции из reaction_list, будет удалена реакции из бд
    
    # добавим метод для получения реакций в виде: {"like": 5}
    @property
    def reactions(self) -> dict[TypeReactionEnum, int]:
        from collections import Counter

        counts = {reaction_type: 0 for reaction_type in TypeReactionEnum}
        actual_counts = Counter(r.reaction_type for r in self.reactions_list)
        counts.update(actual_counts)
        
        return counts
    

    
    
    