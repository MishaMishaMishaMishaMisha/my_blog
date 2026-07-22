from pydantic import BaseModel, Field
from uuid import UUID
from source.core.types import TypeReactionEnum
from source.schemas.attachment import AttachmentDTO


class PostAddDTO(BaseModel):
    title: str = Field(..., max_length=120)
    body: str
    files_id: list[UUID] | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    
class PostPatchDTO(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    body: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    files_id: list[UUID] | None = Field(default=None)
    
class PostAddReactionDTO(BaseModel):
    post_id: UUID
    reaction_type: TypeReactionEnum
    
# response
class TagDTO(BaseModel):
    id: UUID
    name: str = Field(..., max_length=50)
    
    model_config = {'from_attributes': True}
    
class PostWithoutRelationsDTO(BaseModel):
    id: UUID
    title: str
    body: str
    attachments: list[AttachmentDTO]
    author_id: UUID
    views_count: int

    model_config = {'from_attributes': True}
class PostWithTagsDTO(PostWithoutRelationsDTO):
    tags: list[TagDTO]
class PostWithReactionsDTO(PostWithoutRelationsDTO):
    reactions: dict[TypeReactionEnum, int]
class PostFullDTO(PostWithoutRelationsDTO):
    tags: list[TagDTO]
    reactions: dict[TypeReactionEnum, int]
    comments_count: int = 0
    
    
class PostPreviewDTO(BaseModel):
    id: UUID
    author_id: UUID
    title: str
    views_count: int
    comments_count: int = 0
    tags: list[TagDTO]
    
    model_config = {'from_attributes': True}
    
    
class PostListDTO(BaseModel):
    total_count: int
    posts: list[PostPreviewDTO]
    
    model_config = {'from_attributes': True}
    
    
    