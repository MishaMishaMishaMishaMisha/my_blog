from pydantic import BaseModel, Field
from uuid import UUID


class TagCreateDTO(BaseModel):
    id: UUID | None = Field(default=None)
    name: str

class TagDTO(BaseModel):
    id: UUID
    name: str = Field(..., max_length=50)
    
    model_config = {'from_attributes': True}