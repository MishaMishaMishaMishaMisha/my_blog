import uuid

from sqlalchemy import text, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.models.base import BaseORMModel
from source.core.types import TypeReactionEnum

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from source.models.user import UserModel
    from source.models.comment import CommentModel


# здесь будут сохранены реакции на комментарии 
class CommentReactionModel(BaseORMModel):
    __tablename__ = "comment_reactions"
    
    comment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"),
                                               primary_key=True,
                                               index=True)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                              primary_key=True,
                                              index=True)
    
    reaction_type: Mapped[TypeReactionEnum] = mapped_column(SQLEnum(TypeReactionEnum, native_enum=False), 
                                                        nullable=False)
    
    # комментарий под которым оставлена реакция
    comment: Mapped["CommentModel"] = relationship(back_populates="reactions_list")
    
    # пользователь оставивший реакию
    user: Mapped["UserModel"] = relationship(back_populates="user_reactions_on_comments")