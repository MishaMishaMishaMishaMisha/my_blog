from fastapi import APIRouter
from fastapi import Depends
from source.schemas.attachment import AttachmentDTO
from source.services.mediafile import MediaFileService
from source.dependencies.mediafile import get_mediafile_service
from source.core.exceptions import FileAddingException, NotAllowedFileTypeException, FileWritingException, FileNotFoundException
from fastapi import HTTPException
from source.core.logger import default_logger
from source.dependencies.auth import get_user_from_token
from source.models.user import UserModel
from fastapi import UploadFile, File
from uuid import UUID


router = APIRouter(prefix="/upload", tags=["Uploads"])



@router.post("/", response_model=AttachmentDTO)
async def upload_file(file: UploadFile = File(...),
                 user: UserModel = Depends(get_user_from_token),
                 mediafile_service: MediaFileService = Depends(get_mediafile_service)) -> AttachmentDTO:

    try:
        default_logger.info("Uploading file: trying")
        
        file_dto = await mediafile_service.add_file(file, user.id)
        return file_dto
        #return AttachmentDTO.model_validate(file_model)
        # return AttachmentDTO(id=file_model.id,
        #                      file_type=file_model.file_type,
        #                      url=str(STORAGE_PATH / PathDir(file_model.filename)))
    
    except NotAllowedFileTypeException as e:
        raise HTTPException(status_code=415, detail=str(e))
    
    except (FileWritingException, FileAddingException) as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/{file_id}")
async def delete_file(file_id: UUID, 
                 mediafile_service: MediaFileService = Depends(get_mediafile_service)):

    try:
        default_logger.info("Deleting file: trying")
        
        await mediafile_service.delete_file(file_id)
        default_logger.info("Deleting file: file deleted")
        return {"message": "file deleted successfully"}
    
    except FileNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


