from fastapi import APIRouter
from fastapi import Depends
from source.database.db_connect import get_db
from source.models.user import UserModel
from source.schemas.user import UserAddDTO, UserDTO, UserPatchDTO
from source.services.user import UserService
from source.services.email import EmailService
from source.dependencies.user import get_user_service
from source.dependencies.verify_user import get_verify_user_service
from source.core.exceptions import (UsernameAlreadyExsistsException, 
                                    UserNotFoundException, 
                                    EmailAlreadyExsistsException,
                                    InvalidTokenException,
                                    UserInactiveException,
                                    UserAlreadyVerifiedException)
from fastapi import HTTPException
from source.core.logger import default_logger
from source.dependencies.auth import get_user_from_token, CheckUserRole
from source.core.types import RoleEnum, USER_ID_TYPE, OFFSET_QUERY, LIMIT_QUERY
from typing import Sequence
from typing import Annotated
from fastapi import Query
from source.tasks.email_task import send_message_to_email
from source.services.verify_user import VerifyUserService


router = APIRouter(prefix="/users", tags=["Users"])



@router.post("/register", response_model=UserDTO)
async def register_user(new_user: UserAddDTO, 
                        user_service: UserService = Depends(get_user_service),
                        verify_user_service: VerifyUserService = Depends(get_verify_user_service)
                        ) -> UserDTO:

    try:
        default_logger.info("Adding new user: TRYING")
        user = await user_service.create_new_user(new_user)
        default_logger.info("Adding new user: USER ADDED")
        
        
        # # verification
        # # add celery later
        # link = email_service.create_verify_link(user.id)
        # msg = email_service.prepareEmailMsg(email_receiver=user.email,
        #                                     message_subject="Link for verification account",
        #                                     message_body=link)
        # email_service.sendEmail(msg)
        
        # send verification link to email (celery)
        default_logger.info("Adding new user: sending verification link to email")
        link = verify_user_service.create_verify_link(user.id)
        send_message_to_email.delay(user_email=user.email, 
                                    msg_subject="Link for verification account", 
                                    msg_body=link)
        
        return user
    
    except (UsernameAlreadyExsistsException, EmailAlreadyExsistsException) as e:
        default_logger.error("Adding new user: Error. Username or email already exists")
        raise HTTPException(status_code=400, detail=str(e))


    

# protected page. only authothicated user allowed
# client must add header: Authorization: Bearer access_token
@router.get("/me", response_model=UserDTO)
async def get_me(user: UserModel = Depends(get_user_from_token)) -> UserDTO:
    default_logger.debug("Getting protected page")
    return UserDTO.model_validate(user)

# security page
# client must add header: Authorization: Bearer access_token
# and have role ADMIN
@router.get("/securitypage")
async def get_security_page(
    user: UserModel = Depends(CheckUserRole(allowed_roles=[RoleEnum.ADMIN]))
) -> dict:
    default_logger.debug("Getting security page")
    return {"message": f"welcome to security page, {user.username}"}


# get users
@router.get("/", response_model=Sequence[UserDTO])
async def get_users(limit: LIMIT_QUERY = 10,
                    offset: OFFSET_QUERY = 0,
                    user_service: UserService = Depends(get_user_service)) -> Sequence[UserDTO]:
    
    
    default_logger.info(f"Getting users from db: limit={limit}, offset={offset}")
    users = await user_service.get_users(limit, offset)
    return users

# find users
@router.get("/search", response_model=Sequence[UserDTO])
async def find_users(name: Annotated[str, Query(..., 
                                                min_length=3, 
                                                max_length=20, 
                                                title="searching username")], 
                     user_service: UserService = Depends(get_user_service)) -> Sequence[UserDTO]:
    
    default_logger.info(f"Finding users by name {name}")
    users = await user_service.find_user_by_name(name)
    
    return users
        


# routers with dynamic parameter

# get user 
@router.get("/{user_id}", response_model=UserDTO)
async def get_user(user_id: USER_ID_TYPE, 
                   user_service: UserService = Depends(get_user_service)) -> UserDTO:
    try:
        default_logger.info("Getting user by id: Trying")
        
        return await user_service.get_user(user_id)
        
    except UserNotFoundException as e:
        default_logger.error("Getting user by id: Error. User not found")
        raise HTTPException(status_code=404, detail=str(e))

# delete user
@router.delete("/{user_id}")
async def delete_user(user_id: USER_ID_TYPE, 
                      user_service: UserService = Depends(get_user_service)) -> dict:
    
    try:
        default_logger.info("Deleting user: trying")
        await user_service.delete_user(user_id)
        return {"message": "user deleted successfully"}
    except UserNotFoundException as e:
        default_logger.error("Deleting user: Error. User not found")
        raise HTTPException(status_code=404, detail=str(e))
    
# update user
@router.patch("/{user_id}", response_model=UserDTO)
async def update_user(user_id: USER_ID_TYPE,
                      user_data: UserPatchDTO,
                      user_service: UserService = Depends(get_user_service)) -> UserDTO:
    try:
        default_logger.info("Updating user: Trying")
        return await user_service.update_user(user_id, user_data)
    
    except UserNotFoundException as e:
        default_logger.error("Updating user: Error. User not found")
        raise HTTPException(status_code=404, detail=str(e))
    
    except (UsernameAlreadyExsistsException, EmailAlreadyExsistsException) as e:
        default_logger.error("Updating user: Error. Such username or email alreay exists")
        raise HTTPException(status_code=400, detail=str(e))
    
