from pydantic import BaseModel, Field
from uuid import UUID
from source.core.types import FileTypeEnum



class AttachmentDTO(BaseModel):
    id: UUID
    url: str # full path to file
    file_type: FileTypeEnum
    
    model_config = {'from_attributes': True}
