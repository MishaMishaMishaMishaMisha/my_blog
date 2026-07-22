from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import text, ForeignKey
from source.models.base import BaseORMModel
import uuid
from source.core.types import TypeReactionEnum
from sqlalchemy import Enum as SQLEnum

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from source.models.user import UserModel
    from source.models.comment import CommentModel


class CommentReactionModel(BaseORMModel):
    __tablename__ = "comment_reactions"
    
    comment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"),
                                               primary_key=True,
                                               index=True)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                              primary_key=True,
                                              index=True)
    
    # здесь будут хранится реакции на комментарии 
    reaction_type: Mapped[TypeReactionEnum] = mapped_column(SQLEnum(TypeReactionEnum, native_enum=False), 
                                                        nullable=False)
    
    # здесь же добавляем связи
    comment: Mapped["CommentModel"] = relationship(back_populates="reactions_list")
    user: Mapped["UserModel"] = relationship(back_populates="user_reactions_on_comments")