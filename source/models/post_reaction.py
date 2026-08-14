import uuid

from sqlalchemy import text, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.models.base import BaseORMModel
from source.core.types import TypeReactionEnum

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from source.models.user import UserModel
    from source.models.post import PostModel


# здесь будут сохранены реакции на пост
class PostReactionModel(BaseORMModel):
    __tablename__ = "post_reactions"
    
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"),
                                               primary_key=True,
                                               index=True)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                              primary_key=True,
                                              index=True)
    
    reaction_type: Mapped[TypeReactionEnum] = mapped_column(SQLEnum(TypeReactionEnum, native_enum=False), 
                                                        nullable=False)
    
    # пост на который оставлена реакция
    post: Mapped["PostModel"] = relationship(back_populates="reactions_list")
    
    # пользователь оставивший реакцию
    user: Mapped["UserModel"] = relationship(back_populates="user_reactions_on_posts")
    
    