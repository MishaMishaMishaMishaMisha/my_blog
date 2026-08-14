from fastapi import (APIRouter, 
                     Depends, 
                     HTTPException, 
                     status, 
                     UploadFile, 
                     File)
from typing import Sequence, Annotated

from source.models.user import UserModel
from source.schemas.attachment import AttachmentDTO
from source.services.mediafile import MediaFileService
from source.dependencies.mediafile import get_mediafile_service
from source.dependencies.auth import get_user_from_token
from source.dependencies.rate_limit import upload_limiter
from source.core.exceptions import (FileAddingException, 
                                    NotAllowedFileTypeException, 
                                    FileWritingException)
from source.core.types import MAX_ATTACHMENTS_IN_POST
from source.core.logger import default_logger


router = APIRouter(prefix="/upload", tags=["Uploads"])


@router.post("/multiple", 
             response_model=Sequence[AttachmentDTO],
             dependencies=[Depends(upload_limiter)])
async def upload_files(
        files: Annotated[list[UploadFile], File(...)],
        user: UserModel = Depends(get_user_from_token),
        mediafile_service: MediaFileService = Depends(get_mediafile_service)) -> Sequence[AttachmentDTO]:

    try:
        default_logger.info(f"Uploading files: {len(files)} files. trying")
        
        if not user.is_verified:
            default_logger.info("Uploading files: User is not verified")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                                detail="Please, verify your email to do this")
        
        if len(files) > MAX_ATTACHMENTS_IN_POST:
            default_logger.error("Uploading files: Error. User uploads too many files")
            e = f"You cannot upload more than {MAX_ATTACHMENTS_IN_POST} files"
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=e)
        
        files_dto = await mediafile_service.add_files(files, user.id)
        
        default_logger.info("Uploading files: files saved")
        
        return files_dto

    except NotAllowedFileTypeException as e:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
                            detail=str(e))

    except (FileWritingException, FileAddingException) as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail=str(e))

@router.post("/one-file", 
             response_model=AttachmentDTO,
             dependencies=[Depends(upload_limiter)])
async def upload_file(file: UploadFile = File(...),
                 user: UserModel = Depends(get_user_from_token),
                 mediafile_service: MediaFileService = Depends(get_mediafile_service)) -> AttachmentDTO:

    try:
        default_logger.info("Uploading file: trying")
        
        if not user.is_verified:
            default_logger.info("Uploading file: User is not verified")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                                detail="Please, verify your email to do this")
        
        file_dto = await mediafile_service.add_file(file, user.id)
        return file_dto
    
    except NotAllowedFileTypeException as e:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
                            detail=str(e))
    
    except (FileWritingException, FileAddingException) as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail=str(e))


# старые файлы удалятся автоматически через некоторое время
# @router.delete("/{file_id}")
# async def delete_file(file_id: UUID, 
#                  mediafile_service: MediaFileService = Depends(get_mediafile_service)) -> dict:

#     default_logger.info("Deleting file from storage: trying")
    
#     await mediafile_service.delete_file_from_storage(file_id)
#     default_logger.info("Deleting file from storage: file deleted")
#     return {"message": "file deleted successfully"}
    


