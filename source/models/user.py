from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import text, String, Enum
from source.models.base import BaseORMModel
from source.core.types import str_20, RoleEnum
from datetime import datetime
import uuid
from sqlalchemy import UUID as SQLAlchemy_UUID
from typing import TYPE_CHECKING

# чтобы IDE не подчеркивала названия моделей в relationship
if TYPE_CHECKING:
    from source.models.post import PostModel
    from source.models.post_reaction import PostReactionModel
    from source.models.comment import CommentModel
    from source.models.comment_reaction import CommentReactionModel


class UserModel(BaseORMModel):
    __tablename__ = "users"
    
    #id: Mapped[int] = mapped_column(primary_key=True)
    
    # используем вместо int, формат UUID
    # UUID это Universally Unique Identifier
    # это строка из 36 символов
    # пример 123e4567-e89b-12d3-a456-426614174000
    
    # as_uuid=True будет автоматически конвертировать UUID строку из бд в
    #   питоновский UUID формат
    # server_default=text("gen_random_uuid()") генерация id будет на стороне бд
    # альтернатива: default=uuid.uuid4 генерация id на стороне python
    id: Mapped[uuid.UUID] = mapped_column(SQLAlchemy_UUID(as_uuid=True),
                                          primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    
    username: Mapped[str_20] = mapped_column(unique=True, index=True)
    
    email: Mapped[str] = mapped_column(unique=True, index=True)
    
    password_hash: Mapped[str] = mapped_column(String(255))
    
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, native_enum=False), 
        default=RoleEnum.USER, 
        server_default=RoleEnum.USER.value
    )
    
    # это не online/offline а активный ли аккаунт или он забанен например
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    
    # подтвержена ли почта
    is_verified: Mapped[bool] = mapped_column(default=False, server_default=text("false"))

    # последний успешный вход в аккаунт
    last_login: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )
    
    # последняя активность (операции где нужна авторизация)
    last_seen: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )
    
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())"))
    
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())"),
        server_onupdate=text("TIMEZONE('utc', now())"))
    
    
    """Связи"""
    # список постов пользователя
    posts: Mapped[list["PostModel"]] = relationship(back_populates="author")

    # список оставленных реакций на постах
    user_reactions_on_posts: Mapped[list["PostReactionModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    
    # список оставленных комментариев
    comments: Mapped[list["CommentModel"]] = relationship(back_populates="author")
    
    # список оставленных реакций на комментариях
    user_reactions_on_comments: Mapped[list["CommentReactionModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    
    
    