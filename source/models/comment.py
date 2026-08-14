import uuid

from datetime import datetime
from sqlalchemy import text, ForeignKey, String, DateTime
from sqlalchemy import UUID as SQLAlchemy_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.models.base import BaseORMModel
from source.core.types import TypeReactionEnum

# чтобы IDE не подчеркивала названия моделей в relationship
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from source.models.user import UserModel
    from source.models.comment_reaction import CommentReactionModel
    from source.models.post import PostModel
    from source.models.attachment_media import AttachmentMediaModel


class CommentModel(BaseORMModel):
    __tablename__ = "comments"
    
    id: Mapped[uuid.UUID] = mapped_column(SQLAlchemy_UUID(as_uuid=True),
                                          primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    
    body: Mapped[str] = mapped_column(String(2000))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"))
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        server_onupdate=text("now()"))
    

    # id комментария на который отвечает этот комментарий
    # если None, значит это корневой комментарий
    # здесь реализована связь на саму себя
    # внешний ключ ссылается на id из этой же таблицы
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), 
        index=True, 
        nullable=True
    )
    
    
    """Связи"""
    
    # список файлов использованных в комментарии
    attachments: Mapped[list[AttachmentMediaModel]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan"
    )
    
    # комментарий на который отвечает этот коммент.
    # так как в таблице внешний ключ ссылается на эту же таблице,
    # то sqlalchemy начинает путаться в колонках id,parent_id что от чего зависит.
    # remote_side=[id] говорит алхимии что колонка id главная, а parent_id зависимая
    parent: Mapped["CommentModel | None"] = relationship(back_populates="replies",
                                                         remote_side=[id])
    
    # список прямых ответов на этот коммент
    # при удалении главного коммента, удаляются все ответы
    # remote_side указывать не нужно так как в parent уже указано,
    # а обратная связь back_populates говорит алхимии что просто делаем все наоборот
    # идем не снизу вверх (к parent), а сверху вниз
    replies: Mapped[list["CommentModel"]] = relationship(back_populates="parent",
                                                         cascade="all, delete-orphan")
    

    # автор комментария
    author: Mapped["UserModel"] = relationship(back_populates="comments")
    
    # пост под которым оставлен комментарий
    post: Mapped["PostModel"] = relationship(back_populates="comments")

    # список реакций у этого комментрия оставленных пользователями
    reactions_list: Mapped[list["CommentReactionModel"]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan")
    
    # добавим метод для получения реакций в виде: {"like": 5}
    @property
    def reactions(self) -> dict[TypeReactionEnum, int]:
        from collections import Counter

        counts = {reaction_type: 0 for reaction_type in TypeReactionEnum}
        actual_counts = Counter(r.reaction_type for r in self.reactions_list)
        counts.update(actual_counts)
        
        return counts
    