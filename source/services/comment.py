from source.repositories.comment import CommentRepository
from source.models.comment import CommentModel
from source.schemas.comment import CommentAddDTO, CommentPatchDTO, CommentAddReactionDTO
from source.schemas.comment import CommentWithReactionsDTO, CommentWithoutRelationsDTO
from source.core.logger import default_logger
from uuid import UUID
from source.core.types import TypeReactionEnum
from typing import Sequence, Set
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.orm.interfaces import ORMOption
from enum import Enum
from source.cache.redis_backend import RedisBackend



class CommentLoadRelations(str, Enum):
    AUTHOR = "author"
    POST = "post"
    ATTACHMENTS = "attachments"
    REPLIES = "replies"
    REACTIONS = "reactions"
    PARENT = "parent"
    


class CommentService:
    
    _LOAD_MAP = {
        CommentLoadRelations.AUTHOR: joinedload(CommentModel.author),
        CommentLoadRelations.POST: joinedload(CommentModel.post),
        CommentLoadRelations.ATTACHMENTS: selectinload(CommentModel.attachments),
        CommentLoadRelations.REPLIES: selectinload(CommentModel.replies),
        CommentLoadRelations.REACTIONS: selectinload(CommentModel.reactions_list),
        CommentLoadRelations.PARENT: selectinload(CommentModel.parent)
    }
    
    
    def __init__(self, comment_repo: CommentRepository, cache_redis: RedisBackend):
        self.comment_repo = comment_repo
        self.cache_redis = cache_redis
        
    async def create_new_comment(self, new_comment: CommentAddDTO, 
                                 author_id: UUID) -> CommentWithoutRelationsDTO: 
        
        # новый коммент появится в комментах под постом через минуту когда обновится кеш
        
        if new_comment.parent_id:
            _ = await self.comment_repo.get_comment_by_id(new_comment.parent_id)
            #_ = await self.get_comment_by_id(new_comment.parent_id)
            # if parent comment not found, will be raise error
               
        db_comment = await self.comment_repo.add_comment(new_comment, author_id)
        return CommentWithoutRelationsDTO.model_validate(db_comment)
    
    async def delete_comment(self, comment_id: UUID, user_id: UUID):
        await self.comment_repo.delete_comment(comment_id, user_id)
    
    async def get_comment_by_id(self, comment_id: UUID,
                                include: Set[CommentLoadRelations] | None = None) -> CommentWithReactionsDTO:
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        comment_db = await self.comment_repo.get_comment_by_id(comment_id, options)
        default_logger.debug("Getting comment: comment found")
        
        return CommentWithReactionsDTO.model_validate(comment_db)
    
    async def add_reaction_to_comment(self, reaction_data: CommentAddReactionDTO, user_id: UUID):
        await self.comment_repo.add_reaction_to_comment(reaction_data, user_id)
    
    async def update_comment(self, 
                             comment_id: UUID, 
                             author_id: UUID, 
                             comment_data: CommentPatchDTO) -> CommentWithoutRelationsDTO:
        
        comment_db = await self.comment_repo.update_comment(comment_id, author_id, comment_data)
        return CommentWithoutRelationsDTO.model_validate(comment_db)
    
    async def get_all_comment_reactions(self, comment_id: UUID) -> dict[TypeReactionEnum, int]:
        return await self.comment_repo.get_all_comment_reactions(comment_id)
    
    async def get_all_post_root_comments(self, 
            post_id: UUID, 
            limit: int, offset: int,
            include: Set[CommentLoadRelations] | None = None) -> Sequence[CommentWithReactionsDTO]:
        
        key = f"comments:post{post_id}:offset:{offset}:limit:{limit}"
        comments_cached = await self.cache_redis.get(key=key)
        if comments_cached:
            default_logger.debug("Getting comments: getting comments from cache")
            return [CommentWithReactionsDTO.model_validate(comment_dict) for comment_dict in comments_cached]
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
            
        comments_data = await self.comment_repo.get_post_root_comments(post_id, limit, offset, options)
        
        comments = []
        for comment_model, count_replies in comments_data:
            dto = (CommentWithReactionsDTO
                .model_validate(comment_model)
                .model_copy(update={"count_replies": count_replies}))
            comments.append(dto)
            
        default_logger.debug("Getting comments: adding posts in cache")
        # add comments to cache for 1 minute
        comments_cache = [comment.model_dump(mode="json") for comment in comments]
        await self.cache_redis.set(key=key, value=comments_cache, ttl_seconds=60)
        
        return comments
        
    async def get_comment_root_replies(self, comment_id: UUID, 
                limit: int, offset: int,
                include: Set[CommentLoadRelations] | None = None) -> list[CommentWithReactionsDTO]:

        key = f"comment-replies:parent{comment_id}:offset:{offset}:limit:{limit}"
        replies_cached = await self.cache_redis.get(key=key)
        if replies_cached:
            default_logger.debug("Getting comment replies: getting replies from cache")
            return [CommentWithReactionsDTO.model_validate(replie_dict) for replie_dict in replies_cached]

        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)

        replies_data = await self.comment_repo.get_comment_root_replies(comment_id, limit, offset, options)
    
        replies = []
        for comment_model, count_replies in replies_data:
            dto = (CommentWithReactionsDTO
                .model_validate(comment_model)
                .model_copy(update={"count_replies": count_replies}))
            replies.append(dto)
            
        default_logger.debug("Getting comment replies: adding replies in cache")
        # add replies to cache for 1 minute
        replies_cache = [replie.model_dump(mode="json") for replie in replies]
        await self.cache_redis.set(key=key, value=replies_cache, ttl_seconds=60)
            
        return replies


    
    def add_loading_options(self, include: Set[CommentLoadRelations]) -> Sequence[ORMOption]:
        return [self._LOAD_MAP[rel] for rel in include if rel in self._LOAD_MAP]