import uuid

from datetime import datetime
from sqlalchemy import text, DateTime
from sqlalchemy import UUID as SQLAlchemy_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.models.base import BaseORMModel
from source.core.types import str_50

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from source.models.post import PostModel



class TagModel(BaseORMModel):
    __tablename__ = "tags"
    
    id: Mapped[uuid.UUID] = mapped_column(SQLAlchemy_UUID(as_uuid=True),
                                          primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    
    name: Mapped[str_50] = mapped_column(unique=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"))
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        server_onupdate=text("now()"))


    # список постов с этим тегом
    posts_with_tag: Mapped[list["PostModel"]] = relationship(back_populates="tags", secondary="post_tags")

    
    
    
    