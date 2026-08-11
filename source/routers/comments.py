from fastapi import APIRouter
from fastapi import Depends
from source.database.db_connect import get_db
from source.schemas.comment import CommentAddDTO, CommentAddReactionDTO, CommentPatchDTO
from source.schemas.comment import CommentWithParentDTO, CommentWithReactionsDTO, CommentWithRepliesDTO, CommentFullDTO, CommentWithoutRelationsDTO
from source.services.comment import CommentService
from source.dependencies.comment import get_comment_service
from source.core.exceptions import PostNotFoundException, CommentNotFoundException, FileNotFoundException
from fastapi import HTTPException
from source.core.logger import default_logger
from source.dependencies.auth import get_user_from_token, get_user_or_none_from_token
from source.models.user import UserModel
from typing import Sequence
from fastapi import Query, Path
from source.core.types import POST_ID_TYPE, COMMENT_ID_TYPE, LIMIT_QUERY, OFFSET_QUERY, TypeReactionEnum, MAX_ATTACHMENTS_IN_COMMENT
from source.services.comment import CommentLoadRelations
from source.dependencies.rate_limit import (create_comment_limiter,
                                            get_root_comments_limiter,
                                            get_root_replies_limiter,
                                            react_to_comment_limiter,
                                            delete_comment_limiter,
                                            update_comment_limiter)


router = APIRouter(tags=["Comments"])




# create comment on post
@router.post("/posts/{post_id}/comments", 
             response_model=CommentWithoutRelationsDTO,
             dependencies=[Depends(create_comment_limiter)])
async def create_comment(
                post_id: POST_ID_TYPE,
                new_comment: CommentAddDTO, 
                user: UserModel = Depends(get_user_from_token),
                comment_service: CommentService = Depends(get_comment_service)) -> CommentWithoutRelationsDTO:

    try:
        default_logger.info("Adding new comment: TRYING")
        
        if not user.is_verified:
            default_logger.info("User is not verified")
            raise HTTPException(status_code=403, detail="Please, verify your email to do this")
        
        if new_comment.files_id and len(new_comment.files_id) > MAX_ATTACHMENTS_IN_COMMENT:
            default_logger.error("Adding new comment: Error. User attach to many files in comment")
            e = f"You cannot attach in comment more than {MAX_ATTACHMENTS_IN_COMMENT} files"
            raise HTTPException(status_code=403, detail=e)
        
        comment = await comment_service.create_new_comment(new_comment, user.id, post_id)
        comment.author_username = user.username
        default_logger.info("Adding new comment: COMMENT ADDED")
        return comment
    
    except CommentNotFoundException as e:
        default_logger.error("Adding new comment: Error. Parent comment not found")
        raise HTTPException(status_code=404, detail="Parent comment not found")
    
    except FileNotFoundException as e:
        default_logger.error("Adding new comment: Error with files")
        raise HTTPException(status_code=500, detail="Error with files")
    
    
# get post' root comments
@router.get("/posts/{post_id}/comments", 
            response_model=Sequence[CommentWithReactionsDTO],
            dependencies=[Depends(get_root_comments_limiter)])
async def get_post_root_comments(
            post_id: POST_ID_TYPE,
            limit: LIMIT_QUERY = 10,
            offset: OFFSET_QUERY = 0,
            user: UserModel | None = Depends(get_user_or_none_from_token),
            post_service: CommentService = Depends(get_comment_service)) -> Sequence[CommentWithReactionsDTO]:
    
    try:
        default_logger.info("Getting comment of post from db: trying")
        
        user_id = user.id if user else None
        
        comments = await post_service.get_all_post_root_comments(user_id, post_id, limit, offset, 
                                                                 include={CommentLoadRelations.REACTIONS,
                                                                          CommentLoadRelations.ATTACHMENTS})
            
        return comments
    
    except PostNotFoundException as e:
        default_logger.error("Getting comment of post from db: Error. Post not found or no comments")
        raise HTTPException(status_code=404, detail=str(e))

# add reaction to comment
@router.post("/comments/react",
             dependencies=[Depends(react_to_comment_limiter)])
async def add_reaction(
        comment_reaction: CommentAddReactionDTO,
        user: UserModel = Depends(get_user_from_token), 
        comment_service: CommentService = Depends(get_comment_service)
        ) -> dict[str, TypeReactionEnum | None]:
    
    try:
        
        default_logger.info("Adding reaction to comment: trying")
        res = await comment_service.add_reaction_to_comment(comment_reaction, user.id)
        
        return {"user_reaction": res[1]}
    
    except CommentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    

# delete comment
@router.delete("/comments/{comment_id}",
               dependencies=[Depends(delete_comment_limiter)])
async def delete_comment(comment_id: COMMENT_ID_TYPE,
                         user: UserModel = Depends(get_user_from_token), 
                         comment_service: CommentService = Depends(get_comment_service)) -> dict:
    try:
        default_logger.info("Try to delete comment")
        
        if not user.is_verified:
            default_logger.info("User is not verified")
            raise HTTPException(status_code=403, detail="Please, verify your email to do this")
        
        await comment_service.delete_comment(comment_id, user.id)
        default_logger.info("Comment deleted") 
        return {"message": "post deleted from db"}
    
    except CommentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

# update comment
@router.patch("/comments/{comment_id}", 
              response_model=CommentWithoutRelationsDTO,
              dependencies=[Depends(update_comment_limiter)])
async def update_post(
            comment_id: COMMENT_ID_TYPE,
            comment_data: CommentPatchDTO,
            user: UserModel = Depends(get_user_from_token), 
            comment_service: CommentService = Depends(get_comment_service)) -> CommentWithoutRelationsDTO:
    
    try:
        default_logger.info("Updating comment: Trying")
        
        if not user.is_verified:
            default_logger.info("User is not verified")
            raise HTTPException(status_code=403, detail="Please, verify your email to do this")
        
        return await comment_service.update_comment(comment_id, user.id, comment_data)
    
    except CommentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    
# get comment by id
@router.get("/comments/{comment_id}", response_model=CommentWithReactionsDTO)
async def get_comment(
            comment_id: COMMENT_ID_TYPE, 
            comment_service: CommentService = Depends(get_comment_service)) -> CommentWithReactionsDTO:
    try:
        
        default_logger.info("Try to get comment by id")
        comment = await comment_service.get_comment_by_id(comment_id,
                                                                include={CommentLoadRelations.ATTACHMENTS,
                                                                         CommentLoadRelations.REACTIONS})
        
        return comment
        
    except CommentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


# get reactions of comment
@router.get("/comments/{comment_id}/reactions")
async def get_comment_reactions(
    comment_id:COMMENT_ID_TYPE, 
    comment_service: CommentService = Depends(get_comment_service)) -> dict[TypeReactionEnum, int]:

    try:
        
        default_logger.info(f"Getting all reactions of comment={comment_id}")
        return await comment_service.get_all_comment_reactions(comment_id)
    
    except CommentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


# get comment root replies
@router.get("/comments/{comment_id}/replies", 
            response_model=Sequence[CommentWithReactionsDTO],
            dependencies=[Depends(get_root_replies_limiter)])
async def get_comment_root_replies(
    comment_id:COMMENT_ID_TYPE, 
    limit: LIMIT_QUERY = 10,
    offset: OFFSET_QUERY = 0,
    user: UserModel | None = Depends(get_user_or_none_from_token),
    comment_service: CommentService = Depends(get_comment_service)) -> Sequence[CommentWithReactionsDTO]:

    try:
        
        default_logger.info(f"Getting replies of comment={comment_id}")
        
        user_id = user.id if user else None
        
        replies = await comment_service.get_comment_root_replies(user_id, comment_id, limit, offset,
                                                                 include={CommentLoadRelations.ATTACHMENTS,
                                                                          CommentLoadRelations.REACTIONS})
            
        return replies
    
    except CommentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

