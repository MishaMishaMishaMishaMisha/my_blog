from fastapi import APIRouter
from fastapi import Depends
from source.database.db_connect import get_db
from source.schemas.post import PostAddDTO, PostPatchDTO, PostAddReactionDTO, TagDTO
from source.schemas.post import PostPreviewDTO, PostWithTagsDTO, PostListDTO, PostFullDTO
from source.services.post import PostService
from source.dependencies.post import get_post_service
from source.core.exceptions import PostNotFoundException, FileNotFoundException
from fastapi import HTTPException
from source.core.logger import default_logger
from source.dependencies.auth import get_user_from_token
from source.models.user import UserModel
from typing import Sequence, Annotated
from fastapi import Query, Path
from source.services.post import PostLoadRelations, TagLoadRelations
from source.core.types import (POST_ID_TYPE, LIMIT_QUERY, OFFSET_QUERY, 
                               TypeReactionEnum, MAX_ATTACHMENTS_IN_POST,
                               SORT_QUERY, PERIOD_QUERY, PostsSortEnum, PeriodEnum)


router = APIRouter(prefix="/posts", tags=["Posts"])

# сначала идут статические адреса
# потом динамические /{post_id}

####################################################
            # СТАТИЧЕСКИЕ АДРЕСА #
####################################################

# create post
@router.post("/", response_model=PostWithTagsDTO)
async def create_post(new_post: PostAddDTO, 
                      user: UserModel = Depends(get_user_from_token),
                      post_service: PostService = Depends(get_post_service)) -> PostWithTagsDTO:

    try:
        default_logger.info("Adding new post: TRYING")
        
        if new_post.files_id and len(new_post.files_id) > MAX_ATTACHMENTS_IN_POST:
            default_logger.error("Adding new post: Error. User attach to many files in post")
            e = f"You cannot attach in post more than {MAX_ATTACHMENTS_IN_POST} files"
            raise HTTPException(status_code=403, detail=e)
        
        post = await post_service.create_new_post(new_post, user.id)
        default_logger.info("Adding new post: POST ADDED")
        return post 
    except FileNotFoundException as e:
        default_logger.error("Adding new post: Error with files")
        raise HTTPException(status_code=500, detail="Error with files")
            

    
# get posts
@router.get("/", response_model=PostListDTO)
async def get_posts(limit: LIMIT_QUERY = 10,
                    offset: OFFSET_QUERY = 0,
                    sort: SORT_QUERY = PostsSortEnum.NEW,
                    period: PERIOD_QUERY = PeriodEnum.ALL_TIME,
                    post_service: PostService = Depends(get_post_service)) -> PostListDTO:
    
    default_logger.info("Getting posts from db")
    posts_list = await post_service.get_posts(limit, offset, 
                                       sort, period,
                                       include={PostLoadRelations.TAGS})
    
    return posts_list

# add reaction to post
@router.post("/react")
async def add_reaction(post_reaction: PostAddReactionDTO,
                       user: UserModel = Depends(get_user_from_token), 
                       post_service: PostService = Depends(get_post_service)) -> dict:
    
    try:
        default_logger.info("Adding reaction to post: trying")
        await post_service.add_reaction_to_post(post_reaction, user.id)
        return {"message": "reaction added"}
    except PostNotFoundException as e:
        default_logger.error("Adding reaction to post: Error. Post not found")
        raise HTTPException(status_code=404, detail=str(e))
    
# get all existing tags
@router.get("/tags", response_model=Sequence[TagDTO])
async def get_all_tags(limit: LIMIT_QUERY = 10, 
                       offset: OFFSET_QUERY = 0,
                       post_service: PostService = Depends(get_post_service)) -> Sequence[TagDTO]:

    default_logger.info("Getting all existing tags")
    return await post_service.get_all_existing_tags(limit, offset)

# find posts
@router.get("/search", response_model=Sequence[PostPreviewDTO])
async def find_posts(
            title: Annotated[str, Query(..., 
                                        min_length=3, 
                                        max_length=120, 
                                        title="searching post title")],
            limit: LIMIT_QUERY = 10, 
            offset: OFFSET_QUERY = 0,
            post_service: PostService = Depends(get_post_service)) -> Sequence[PostPreviewDTO]:
    
    default_logger.info("Finding posts by title: Trying")
    posts = await post_service.find_post_by_title(title, limit, offset, include={PostLoadRelations.TAGS})
    
    default_logger.debug(f"Finding posts by title: found {len(posts)} posts")

    return posts

# find tags
@router.get("/tags/search", response_model=Sequence[TagDTO])
async def find_tags(
            name: Annotated[str, Query(..., 
                                        min_length=3, 
                                        max_length=120, 
                                        title="searching post title")], 
            post_service: PostService = Depends(get_post_service)) -> Sequence[TagDTO]:
    
    default_logger.info(f"Finding tags by name {name}")
    return await post_service.find_tags_by_name(name)


####################################################
            # ДИНАМЕЧЕСКИЕ АДРЕСА #
####################################################

# delete post
@router.delete("/{post_id}")
async def delete_post(post_id: POST_ID_TYPE,
                      user: UserModel = Depends(get_user_from_token), 
                      post_service: PostService = Depends(get_post_service)) -> dict:
    try:
        default_logger.info("Try to delete post")
        await post_service.delete_post(post_id, user.id)
        return {"message": "post deleted from db"}
    except PostNotFoundException as e:
        default_logger.error("Try to delete post: Error. Post not found")
        raise HTTPException(status_code=404, detail=str(e))

# update post
@router.patch("/{post_id}", response_model=PostWithTagsDTO)
async def update_post(post_id: POST_ID_TYPE,
                      post_data: PostPatchDTO,
                      user: UserModel = Depends(get_user_from_token), 
                      post_service: PostService = Depends(get_post_service)) -> PostWithTagsDTO:
    try:
        default_logger.info("Updating post: Trying")
        
        updated_post = await post_service.update_post(post_id, user.id, post_data)
        return updated_post
    
    except PostNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

# get post with increment count views
@router.get("/{post_id}", response_model=PostFullDTO)
async def get_post_with_increment_views(
            post_id: POST_ID_TYPE, 
            post_service: PostService = Depends(get_post_service)) -> PostFullDTO:
    try:
        default_logger.info("Try to get post")
        post = await post_service.get_post_with_increment_views(
                                            post_id,
                                            include={PostLoadRelations.TAGS, 
                                                     PostLoadRelations.REACTIONS, 
                                                     PostLoadRelations.ATTACHMENTS})
        
        return post
        
    except PostNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

# get tags of post
@router.get("/{post_id}/tags", response_model=Sequence[TagDTO])
async def get_post_tags(
    post_id: POST_ID_TYPE, 
    post_service: PostService = Depends(get_post_service)) -> Sequence[TagDTO]:

    try:
        default_logger.info(f"Getting all tags of post")
        return await post_service.get_all_post_tags(post_id)
    
    except PostNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

# get reactions of post
@router.get("/{post_id}/reactions")
async def get_post_reactions(
    post_id: POST_ID_TYPE, 
    post_service: PostService = Depends(get_post_service)) -> dict[TypeReactionEnum, int]:

    try:
        default_logger.info("Getting all reactions of post")
        return await post_service.get_all_post_reactions(post_id)
    except PostNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

        



