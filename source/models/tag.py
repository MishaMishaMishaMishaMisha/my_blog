from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import text
from source.models.base import BaseORMModel
from source.core.types import str_50
from datetime import datetime
import uuid
from sqlalchemy import UUID as SQLAlchemy_UUID
from typing import TYPE_CHECKING

# чтобы IDE не подчеркивала названия моделей в relationship
if TYPE_CHECKING:
    from source.models.post import PostModel



class TagModel(BaseORMModel):
    __tablename__ = "tags"
    
    id: Mapped[uuid.UUID] = mapped_column(SQLAlchemy_UUID(as_uuid=True),
                                          primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    
    name: Mapped[str_50] = mapped_column(unique=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())"))
    
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())"),
        server_onupdate=text("TIMEZONE('utc', now())"))


    # список постов с этим тегом
    posts_with_tag: Mapped[list["PostModel"]] = relationship(back_populates="tags", secondary="post_tags")

    
    
    
    