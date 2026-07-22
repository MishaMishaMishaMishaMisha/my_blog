from source.repositories.post import PostRepository
from source.models.post import PostModel
from source.models.user import UserModel
from source.models.tag import TagModel
from source.schemas.post import PostAddDTO, PostPatchDTO, PostAddReactionDTO
from source.core.logger import default_logger
from uuid import UUID
from source.core.types import TypeReactionEnum
from typing import Sequence, Set
from sqlalchemy.orm import selectinload, joinedload
from enum import Enum
from sqlalchemy.orm.interfaces import ORMOption
from source.core.types import PostsSortEnum, PeriodEnum
from source.schemas.post import PostPreviewDTO, PostWithTagsDTO, PostListDTO, PostFullDTO, TagDTO
from source.cache.redis_backend import RedisBackend


from source.tasks.views_count_task import update_views_count


class PostLoadRelations(str, Enum):
    AUTHOR = "author"
    TAGS = "tags"
    ATTACHMENTS = "attachments"
    COMMENTS = "comments"
    REACTIONS = "reactions"
    
class TagLoadRelations(str, Enum):
    POSTS_WITH_TAG = "posts_with_tag"


class PostService:
    
    _LOAD_MAP = {
        PostLoadRelations.AUTHOR: joinedload(PostModel.author),
        PostLoadRelations.TAGS: selectinload(PostModel.tags),
        PostLoadRelations.ATTACHMENTS: selectinload(PostModel.attachments),
        PostLoadRelations.COMMENTS: selectinload(PostModel.comments),
        PostLoadRelations.REACTIONS: selectinload(PostModel.reactions_list),
        TagLoadRelations.POSTS_WITH_TAG: selectinload(TagModel.posts_with_tag)
    }
    
    
    def __init__(self, post_repo: PostRepository, cache_redis: RedisBackend):
        self.post_repo = post_repo
        self.cache_redis = cache_redis
        
    async def create_new_post(self, new_post: PostAddDTO, author_id: UUID) -> PostWithTagsDTO: 
        
        # новый пост появится в ленте последних постов через минуту когда обновится кеш
               
        db_post = await self.post_repo.add_post(new_post, author_id)
        return PostWithTagsDTO.model_validate(db_post)
    
    async def delete_post(self, post_id: UUID, author_id: UUID):
        # delete post from cache
        await self.cache_redis.delete(key=f"post:{post_id}")
        
        return await self.post_repo.delete_post(post_id, author_id)
    
    async def get_post_with_increment_views(self, 
                    post_id: UUID,
                    include: Set[PostLoadRelations] | None = None) -> PostFullDTO:
        
        # проверяем кеш
        post_cached = await self.cache_redis.get(key=f"post:{post_id}")
        if post_cached:
            
            # сохраняем в кеше открытие этого поста
            await self.cache_redis.hincrby("post_views", str(post_id), 1)
            
            return post_cached
        
        # получаем пост из бд
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        post_data = await self.post_repo.get_post_with_comments_count(post_id, options)

        post = (PostFullDTO
               .model_validate(post_data[0])
               .model_copy(update={"comments_count": post_data[1]}))
        
        # увеличиваем views_count в кеше
        await self.cache_redis.hincrby("post_views", str(post_id), 1)
        
        # добавляем пост в кеш на 10 минут
        await self.cache_redis.set(key=f"post:{post.id}", 
                                   value=post.model_dump(mode="json"), 
                                   ttl_seconds=600)
        
        
        # # test
        # update_views_count.delay()
        
        return post

    
    async def add_reaction_to_post(self, reaction_data: PostAddReactionDTO, user_id: UUID):
        # delete post from cache
        default_logger.debug("Deleting post: deleting post from cache")
        await self.cache_redis.delete(key=f"post:{reaction_data.post_id}")
        
        await self.post_repo.add_reaction_to_post(reaction_data, user_id)
    
    async def update_post(self, post_id: UUID, author_id: UUID, post_data: PostPatchDTO) -> PostWithTagsDTO:
        # delete post from cache
        default_logger.debug("Updating post: deleting post from cache")
        await self.cache_redis.delete(key=f"post:{post_id}")
        
        db_post = await self.post_repo.update_post(post_id, author_id, post_data)
        return PostWithTagsDTO.model_validate(db_post)
    
    async def get_posts(self, 
            limit: int, offset: int, 
            sort: PostsSortEnum, period: PeriodEnum,
            include: Set[PostLoadRelations] | None = None) -> PostListDTO:
        
        # check in cache
        key = ""
        ttl = 0
        if sort == PostsSortEnum.NEW:
            key = f"posts:latest:offset:{offset}:limit:{limit}"
            ttl = 60
        elif sort == PostsSortEnum.POPULAR:
            ttl = 600
            if period == PeriodEnum.ALL_TIME:
                key = f"posts:pupular:all-time:offset:{offset}:limit:{limit}"
            elif period == PeriodEnum.DAY:
                key = f"posts:pupular:day:offset:{offset}:limit:{limit}"
            elif period == PeriodEnum.MONTH:
                key = f"posts:pupular:month:offset:{offset}:limit:{limit}"
            elif period == PeriodEnum.WEEK:
                key = f"posts:pupular:week:offset:{offset}:limit:{limit}"
            elif period == PeriodEnum.YEAR:
                key = f"posts:pupular:year:offset:{offset}:limit:{limit}"
        
        default_logger.debug("Getting posts: checing cache")
        posts_cached = await self.cache_redis.get(key=key)
        if posts_cached:
            default_logger.debug("Getting posts: getting posts from cache")
            return PostListDTO.model_validate(posts_cached)
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        default_logger.debug("Getting posts: get posts from db")
        res = await self.post_repo.get_posts(limit, offset, sort, period, options)

        total_count = res[0]
        posts_data = res[1]
        posts_dto = []
        for post_model, comments_count in posts_data:
            dto = (PostPreviewDTO
                .model_validate(post_model)
                .model_copy(update={"comments_count": comments_count}))
            posts_dto.append(dto)

        posts = PostListDTO(total_count=total_count, posts=posts_dto)
        
        if key:
            default_logger.debug("Getting posts: adding posts in cache")
            # add posts to cache: for 10 minutes if pupalar; for 1 minute if latest
            await self.cache_redis.set(key=key, 
                                       value=posts.model_dump(mode="json"),
                                       ttl_seconds=ttl)
        
        return posts

    async def get_all_existing_tags(self,
                                    limit: int, offset: int,
                                    include: Set[PostLoadRelations] | None = None) -> Sequence[TagDTO]:
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
            
        db_tags = await self.post_repo.get_all_existing_tags(limit, offset, options)
        return [TagDTO.model_validate(tag_model) for tag_model in db_tags]
        
    async def get_all_post_tags(self, post_id: UUID) -> list[TagDTO]:
        db_tags = await self.post_repo.get_all_post_tags(post_id)
        return [TagDTO.model_validate(tag_model) for tag_model in db_tags]
    
    async def get_all_post_reactions(self, post_id: UUID) -> dict[TypeReactionEnum, int]:
        return await self.post_repo.get_all_post_reactions(post_id)
    
    async def find_post_by_title(self, seacrhing_title: str,
                                 limit: int, offset: int,
                                 include: Set[PostLoadRelations] | None = None) -> Sequence[PostPreviewDTO]:
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        res = await self.post_repo.find_post_by_title(seacrhing_title, limit, offset, options)

        posts = []
        for post_model, comments_count in res:
            dto = (PostPreviewDTO
                .model_validate(post_model)
                .model_copy(update={"comments_count": comments_count}))
            posts.append(dto)

        return posts
    
    async def find_tags_by_name(self, seacrhing_tag: str,
                                include: Set[PostLoadRelations] | None = None) -> Sequence[TagDTO]:
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        db_tags = await self.post_repo.find_tags_by_name(seacrhing_tag, options)
        return [TagDTO.model_validate(tag) for tag in db_tags]
    
    
    def add_loading_options(self, include: Set[PostLoadRelations]) -> Sequence[ORMOption]:
        return [self._LOAD_MAP[rel] for rel in include if rel in self._LOAD_MAP]