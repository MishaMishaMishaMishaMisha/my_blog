from fastapi import APIRouter
from fastapi import Depends
from source.database.db_connect import get_db
from source.models.user import UserModel
from source.schemas.user import UserAddDTO, UserDTO, UserPatchDTO, UserPublicProfileDTO
from source.schemas.post import PostListDTO
from source.schemas.comment import CommentWithoutRelationsDTO
from source.services.user import UserService
from source.services.post import PostService
from source.services.comment import CommentService
from source.services.email import EmailService
from source.dependencies.user import get_user_service
from source.dependencies.post import get_post_service
from source.dependencies.comment import get_comment_service
from source.dependencies.verify_user import get_verify_user_service
from source.core.exceptions import (UserException,
                                    UsernameAlreadyExsistsException, 
                                    UserNotFoundException, 
                                    EmailAlreadyExsistsException,
                                    InvalidTokenException,
                                    UserInactiveException,
                                    UserAlreadyVerifiedException,
                                    UserAlreadyCreatedVerifyLink)
from fastapi import HTTPException
from source.core.logger import default_logger
from source.dependencies.auth import get_user_from_token, CheckUserRole
from source.core.types import RoleEnum, USER_ID_TYPE, OFFSET_QUERY, LIMIT_QUERY
from typing import Sequence
from typing import Annotated
from fastapi import Query, Path
from source.tasks.email_task import send_message_to_email
from source.services.verify_user import VerifyUserService
from source.dependencies.rate_limit import (register_rate_limiter,
                                            get_me_limiter,
                                            get_users_limiter,
                                            find_users_limiter,
                                            get_user_profile_limiter,
                                            get_user_posts_limiter,
                                            delete_user_limiter,
                                            update_user_limiter)


router = APIRouter(prefix="/users", tags=["Users"])



@router.post("/register", 
             response_model=UserDTO,
             dependencies=[Depends(register_rate_limiter)])
async def register_user(new_user: UserAddDTO, 
                        user_service: UserService = Depends(get_user_service),
                        verify_user_service: VerifyUserService = Depends(get_verify_user_service)
                        ) -> UserDTO:

    try:
        default_logger.info("Adding new user: TRYING")
        user = await user_service.create_new_user(new_user)
        default_logger.info("Adding new user: USER ADDED")
        
        # send verification link to email (celery)
        default_logger.info("Adding new user: sending verification link to email")
        link = await verify_user_service.create_verify_link(user.id)
        
        send_message_to_email.delay(user_email=user.email, 
                                    msg_subject="Link for verification account", 
                                    msg_body=link)
        
        return user
    
    except (UsernameAlreadyExsistsException, 
            EmailAlreadyExsistsException) as e:
        default_logger.error("Adding new user: Error. Username or email already exists")
        raise HTTPException(status_code=400, detail=str(e))
    
    except UserAlreadyCreatedVerifyLink as e:
        default_logger.error("Adding new user: Error. User already created verify link")
        raise HTTPException(status_code=400, detail=str(e))
    
    except UserException as e:
        default_logger.error(f"Adding new user: Error. unknown inegrity error")
        raise HTTPException(status_code=500, detail="Server cant add new user. Try later")
    


# protected page. only authothicated user allowed
# client must add header: Authorization: Bearer access_token
@router.get("/me", response_model=UserDTO,
            dependencies=[Depends(get_me_limiter)])
async def get_me(user: UserModel = Depends(get_user_from_token)) -> UserDTO:
    default_logger.debug("Getting protected page")
    return UserDTO.model_validate(user)

# test security page
# client must add header: Authorization: Bearer access_token
# and have role ADMIN
@router.get("/securitypage")
async def get_security_page(
    user: UserModel = Depends(CheckUserRole(allowed_roles=[RoleEnum.ADMIN]))
) -> dict:
    default_logger.debug("Getting security page")
    return {"message": f"welcome to security page, {user.username}"}


# get users
@router.get("/", response_model=Sequence[UserDTO], 
            dependencies=[Depends(get_users_limiter)])
async def get_users(limit: LIMIT_QUERY = 10,
                    offset: OFFSET_QUERY = 0,
                    user_service: UserService = Depends(get_user_service)) -> Sequence[UserDTO]:
    
    
    default_logger.info(f"Getting users from db: limit={limit}, offset={offset}")
    users = await user_service.get_users(limit, offset)
    return users

# find users
@router.get("/search", response_model=Sequence[UserDTO], 
            dependencies=[Depends(find_users_limiter)])
async def find_users(name: Annotated[str, Query(..., 
                                                min_length=3, 
                                                max_length=20, 
                                                title="searching username")], 
                     user_service: UserService = Depends(get_user_service)) -> Sequence[UserDTO]:
    
    default_logger.info(f"Finding users by name {name}")
    users = await user_service.find_user_by_name(name)
    
    return users
        


# routers with dynamic parameter

# user profile
@router.get("/{username}", 
            response_model=UserPublicProfileDTO,
            dependencies=[Depends(get_user_profile_limiter)])
async def get_user_profile(
            username: Annotated[str, Path(min_length=5, max_length=20)], 
            user_service: UserService = Depends(get_user_service)) -> UserPublicProfileDTO:
    try:
        default_logger.info("Getting user profile: Trying")
        
        return await user_service.get_user_profile(username)
        
    except UserNotFoundException as e:
        default_logger.error("Getting user profile: Error. User not found")
        raise HTTPException(status_code=404, detail=str(e))
    
# get user posts
@router.get("/{username}/posts", response_model=PostListDTO,
            dependencies=[Depends(get_user_posts_limiter)])
async def get_user_posts(username: Annotated[str, Path(min_length=5, max_length=20)],
                         limit: LIMIT_QUERY = 10,
                         offset: OFFSET_QUERY = 0, 
                         post_service: PostService = Depends(get_post_service)) -> PostListDTO:
    
    default_logger.info("Getting user posts: start...")
    
    posts_list = await post_service.get_user_posts(username, limit, offset)
    
    default_logger.info("Getting user posts: done")
    
    return posts_list

# # get user comments
# @router.get("/{username}/comments", 
#             response_model=CommentWithoutRelationsDTO,
#             dependencies=[Depends(RateLimiter(times=2, seconds=5))])
# async def get_user_comments(
#             username: Annotated[str, Path(min_length=5, max_length=20)],
#             limit: LIMIT_QUERY = 10,
#             offset: OFFSET_QUERY = 0, 
#             comment_service: CommentService = Depends(get_comment_service)) -> CommentWithoutRelationsDTO:
    
#     default_logger.info("Getting user comments: start...")
    
#     posts_list = await post_service.get_user_posts(username, limit, offset)
    
#     default_logger.info("Getting user posts: done")
    
#     return posts_list


# delete user
@router.delete("/me", 
               dependencies=[Depends(delete_user_limiter)])
async def delete_user(user: UserModel = Depends(get_user_from_token),
                      user_service: UserService = Depends(get_user_service)) -> dict:
    
    try:
        default_logger.info("Deleting user: trying")
        await user_service.delete_user(user.id)
        return {"message": "user deleted successfully"}
    except UserNotFoundException as e:
        default_logger.error("Deleting user: Error. User not found")
        raise HTTPException(status_code=404, detail=str(e))
    
# update user
@router.patch("/me", response_model=UserDTO, 
              dependencies=[Depends(update_user_limiter)])
async def update_user(user_data: UserPatchDTO,
                      user: UserModel = Depends(get_user_from_token),
                      user_service: UserService = Depends(get_user_service)) -> UserDTO:
    try:
        default_logger.info("Updating user: Trying")
        
        if not user.is_verified:
            default_logger.info("User is not verified")
            raise HTTPException(status_code=403, detail="Please, verify your email to do this")
        
        return await user_service.update_user(user.id, user_data)
    
    except UserNotFoundException as e:
        default_logger.error("Updating user: Error. User not found")
        raise HTTPException(status_code=404, detail=str(e))
    
    except (UsernameAlreadyExsistsException, EmailAlreadyExsistsException) as e:
        default_logger.error("Updating user: Error. Such username or email alreay exists")
        raise HTTPException(status_code=400, detail=str(e))
    
