from pydantic import BaseModel, Field
from uuid import UUID
from source.core.types import FileTypeEnum



class AttachmentDTO(BaseModel):
    id: UUID
    orig_name: str | None = Field(default=None)
    url: str # full path to file
    file_type: FileTypeEnum
    
    model_config = {'from_attributes': True}
