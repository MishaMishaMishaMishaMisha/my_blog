from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text, ForeignKey
from source.models.base import BaseORMModel
import uuid

class PostTagModel(BaseORMModel):
    __tablename__ = "post_tags"
    
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"),
                                               primary_key=True,
                                               index=True)
    
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"),
                                              primary_key=True,
                                              index=True)
    
    

