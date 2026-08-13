from fastapi import APIRouter
from fastapi import Depends
from source.schemas.attachment import AttachmentDTO
from source.services.mediafile import MediaFileService
from source.dependencies.mediafile import get_mediafile_service
from source.core.exceptions import (FileAddingException, 
                                    NotAllowedFileTypeException, 
                                    FileWritingException, 
                                    FileNotFoundException,
                                    UserNotVerifiedException)
from fastapi import HTTPException
from source.core.logger import default_logger
from source.dependencies.auth import get_user_from_token
from source.models.user import UserModel
from fastapi import UploadFile, File
from uuid import UUID
from typing import Sequence, Annotated
from source.core.types import MAX_ATTACHMENTS_IN_POST
from source.dependencies.rate_limit import upload_limiter


router = APIRouter(prefix="/upload", tags=["Uploads"])



# from source.tasks.delete_mediafiles_task import delete_temp_files, sync_Files_in_Storage_and_in_DB
# @router.post("/test-delete-temp-files")
# async def delete_temp():
#     delete_temp_files.delay()

# @router.post("/test-sync-files")
# async def sync_files():
#     sync_Files_in_Storage_and_in_DB.delay()




@router.post("/multiple", 
             response_model=Sequence[AttachmentDTO],
             dependencies=[Depends(upload_limiter)])
async def upload_files(
        files: Annotated[list[UploadFile], File(...)],
        user: UserModel = Depends(get_user_from_token),
        mediafile_service: MediaFileService = Depends(get_mediafile_service)) -> Sequence[AttachmentDTO]:

    try:
        default_logger.info("Uploading files: trying")
        
        if not user.is_verified:
            default_logger.info("User is not verified")
            raise HTTPException(status_code=403, detail="Please, verify your email to do this")
        
        if len(files) > MAX_ATTACHMENTS_IN_POST:
            default_logger.error("Uploading files: Error. User uploads too many files")
            e = f"You cannot upload so many files"
            raise HTTPException(status_code=403, detail=e)
        
        files_dto = await mediafile_service.add_files(files, user.id)
        
        default_logger.info("Uploading files: files added")
        
        return files_dto

    except NotAllowedFileTypeException as e:
        raise HTTPException(status_code=415, detail=str(e))

    except (FileWritingException, FileAddingException) as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/one-file", 
             response_model=AttachmentDTO,
             dependencies=[Depends(upload_limiter)])
async def upload_file(file: UploadFile = File(...),
                 user: UserModel = Depends(get_user_from_token),
                 mediafile_service: MediaFileService = Depends(get_mediafile_service)) -> AttachmentDTO:

    try:
        default_logger.info("Uploading file: trying")
        
        if not user.is_verified:
            default_logger.info("User is not verified")
            raise HTTPException(status_code=403, detail="Please, verify your email to do this")
        
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


# старые файлы удалятся автоматически через некоторое время
# @router.delete("/{file_id}")
# async def delete_file(file_id: UUID, 
#                  mediafile_service: MediaFileService = Depends(get_mediafile_service)) -> dict:

#     default_logger.info("Deleting file from storage: trying")
    
#     await mediafile_service.delete_file_from_storage(file_id)
#     default_logger.info("Deleting file from storage: file deleted")
#     return {"message": "file deleted successfully"}
    


