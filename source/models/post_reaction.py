from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import text, ForeignKey
from source.models.base import BaseORMModel
import uuid
from source.core.types import TypeReactionEnum
from sqlalchemy import Enum as SQLEnum

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from source.models.user import UserModel
    from source.models.post import PostModel

# в отличие от PostTag эта модель должна хранить данные
# такие модели наз. Assossiation objects
class PostReactionModel(BaseORMModel):
    __tablename__ = "post_reactions"
    
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"),
                                               primary_key=True,
                                               index=True)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                              primary_key=True,
                                              index=True)
    
    # здесь будут хранится реакции на посты
    reaction_type: Mapped[TypeReactionEnum] = mapped_column(SQLEnum(TypeReactionEnum, native_enum=False), 
                                                        nullable=False)
    # nullable=False запрещает хранить null, то есть только корректные реакции
    
    # здесь же добавляем связи
    post: Mapped["PostModel"] = relationship(back_populates="reactions_list")
    user: Mapped["UserModel"] = relationship(back_populates="user_reactions_on_posts")
    
    
"""
пример работы
- создание реакции на посте
new_reaction = PostReactionModel(
    post_id=post_id,
    user_id=user.id,
    reaction_type=TypeReaction.FIRE
)
db_session.add(new_reaction)
await db_session.commit()

- изменение реакции: 
    - поиск по паре user.id,post.id 
    - меняем reation_type
"""