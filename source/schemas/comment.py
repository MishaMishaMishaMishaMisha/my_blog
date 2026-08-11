from pydantic import BaseModel, Field
from uuid import UUID
from source.core.types import TypeReactionEnum
from source.schemas.attachment import AttachmentDTO
from datetime import datetime


class CommentAddDTO(BaseModel):
    parent_id: UUID | None = None
    body: str = Field(max_length=2000)
    files_id: list[UUID] | None = Field(default=None)
    
class CommentPatchDTO(BaseModel):
    body: str | None = Field(default=None, max_length=2000)
    files_id: list[UUID] | None = Field(default=None)
    
class CommentAddReactionDTO(BaseModel):
    comment_id: UUID
    reaction_type: TypeReactionEnum
    
    
# response
class CommentWithoutRelationsDTO(BaseModel):
    id: UUID
    post_id: UUID
    author_id: UUID
    parent_id: UUID | None
    body: str
    attachments: list[AttachmentDTO]
    author_username: str = ""
    created_at: datetime

    model_config = {'from_attributes': True}
    
class CommentWithParentDTO(CommentWithoutRelationsDTO):
    parent: CommentWithoutRelationsDTO
    
class CommentWithRepliesDTO(CommentWithoutRelationsDTO):
    replies: list[CommentWithoutRelationsDTO]
    
class CommentWithReactionsDTO(CommentWithoutRelationsDTO):
    reactions: dict[TypeReactionEnum, int]
    count_replies: int = 0
    created_at: datetime
    # реакция текущего пользователя на комметарий
    user_reaction: TypeReactionEnum | None = None
    
class CommentFullDTO(CommentWithoutRelationsDTO):
    parent: CommentWithoutRelationsDTO
    replies: list[CommentWithoutRelationsDTO]
    reactions: dict[TypeReactionEnum, int]
    created_at: datetime
    user_reaction: TypeReactionEnum | None = None
