import json

from uuid import UUID
from enum import Enum
from typing import Sequence, Set, Any
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.orm.interfaces import ORMOption

from source.cache.redis_backend import RedisBackend
from source.repositories.post import PostRepository
from source.models.post import PostModel
from source.models.tag import TagModel
from source.core.logger import default_logger
from source.core.types import TypeReactionEnum
from source.core.types import PostsSortEnum, PeriodEnum
from source.api.v1.schemas.post import PostAddDTO, PostPatchDTO, PostAddReactionDTO
from source.api.v1.schemas.post import (PostPreviewDTO, 
                                 PostWithTagsDTO, 
                                 PostListDTO, 
                                 PostFullDTO, 
                                 TagDTO,
                                 TagCreateDTO)


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
        
        self.cache_post_preview_key = "post:{post_id}:preview"
        self.cache_post_body_key = "post:{post_id}:body"
        self.cache_post_commentsCount_key = "post:{post_id}:comments_count"
        self.cache_post_reactions_key = "post:{post_id}:reactions"
        self.cache_post_user_reaction_key = "post:{post_id}:user_reaction:{user_id}"
        self.cache_tags_list_key = "tags_list"
        
        self.cache_posts_views = "post_views"
        
        self.cache_post_preview_ttl = 86400 # 1 day
        self.cache_post_body_ttl = 86400
        self.cache_post_commentsCount_ttl = 86400
        self.cache_post_reactions_ttl = 86400
        self.cache_post_user_reaction_ttl = 600 # 10 minutes
        self.cache_tags_list_ttl = 300 # 5 minutes
        
    async def create_new_post(self, new_post: PostAddDTO, author_id: UUID) -> PostWithTagsDTO: 
        
        # добавляем пост в базу
        default_logger.debug("Adding post: adding to db")
        db_post = await self.post_repo.add_post(new_post, author_id)
        dto_post = PostWithTagsDTO.model_validate(db_post)
        default_logger.debug("Adding post: post added to db")
        
        post_id_str = str(dto_post.id)
        
        default_logger.debug("Adding post: adding to cache")
        # Разделяем пост на preview и body для кэша
        preview_data = {
            "id": post_id_str,
            "title": dto_post.title,
            "author_id": str(dto_post.author_id),
            "author_username": db_post.author.username,
            "tags": [t.model_dump(mode="json") for t in dto_post.tags],
            "created_at": db_post.created_at.isoformat(),
            "views_count": dto_post.views_count
        }
        body_data = {
            "body": dto_post.body,
            "attachments": [a.model_dump(mode="json") for a in dto_post.attachments]
        }

        async with self.cache_redis.pipeline(transaction=True) as pipe:
            
            pipe.set(self.cache_post_preview_key.format(post_id=post_id_str), 
                     json.dumps(preview_data), 
                     ex=self.cache_post_preview_ttl)
            pipe.set(self.cache_post_body_key.format(post_id=post_id_str),
                     json.dumps(body_data), 
                     ex=self.cache_post_body_ttl)
            pipe.set(self.cache_post_commentsCount_key.format(post_id=post_id_str),
                     0, 
                     ex=self.cache_post_commentsCount_ttl)
            
            # реакции помечаем как empty
            pipe.hset(self.cache_post_reactions_key.format(post_id=post_id_str), 
                          mapping={"_state": "EMPTY"})
            
            await pipe.execute()

        # обновляем кеш с тегами если были добавлены новые
        if new_post.tags:
            await self._check_if_new_tag_in_cache(new_post.tags)

        default_logger.debug("Adding post: post added to cache")
        
        return dto_post
    
    async def delete_post(self, post_id: UUID, author_id: UUID):
        await self.post_repo.delete_post(post_id, author_id)
        
        default_logger.debug("Deleting post: deleting post from cache")
        post_id_str = str(post_id)
        # Чистим абсолютно все следы поста из Redis
        await self.cache_redis.delete(self.cache_post_preview_key.format(post_id=post_id_str))
        await self.cache_redis.delete(self.cache_post_body_key.format(post_id=post_id_str))
        await self.cache_redis.delete(self.cache_post_commentsCount_key.format(post_id=post_id_str))
        await self.cache_redis.delete(self.cache_post_reactions_key.format(post_id=post_id_str))
    
    async def get_post_with_increment_views(self, 
                    user_id: UUID | None,
                    post_id: UUID,
                    include: Set[PostLoadRelations] | None = None) -> PostFullDTO:
        
        default_logger.debug("Getting post: checking cache")
        
        post_id_str = str(post_id)

        # 1. Достаем ВСЕ ключи через Pipeline
        async with self.cache_redis.pipeline(transaction=False) as pipe:
            pipe.get(self.cache_post_preview_key.format(post_id=post_id_str))
            pipe.get(self.cache_post_body_key.format(post_id=post_id_str))
            pipe.get(self.cache_post_commentsCount_key.format(post_id=post_id_str))
            pipe.hgetall(self.cache_post_reactions_key.format(post_id=post_id_str))
            if user_id:
                pipe.get(self.cache_post_user_reaction_key.format(post_id=post_id_str,
                                                                  user_id=user_id))

            results = await pipe.execute()

        raw_preview, raw_body, raw_comments, raw_reactions = (
            results[0], results[1], results[2], results[3]
        )
        raw_user_reaction = results[4] if user_id else None

        # если в кеше нету preview либо body
        # делаем полный запрос к бд
        if not raw_preview or not raw_body:
            
            default_logger.debug("Getting post: post not in cache. getting post from db")
            
            options = self.add_loading_options(include) if include else None
            post_data = await self.post_repo.get_post_with_data(user_id, post_id, options)
            
            post_dto = (PostFullDTO
                       .model_validate(post_data[0])
                       .model_copy(update={"comments_count": post_data[1]})
                       .model_copy(update={"author_username": post_data[2]})
                       .model_copy(update={"user_reaction": post_data[3]}))

            default_logger.debug("Getting post: post got")

            default_logger.debug("Getting post: adding post to cache")
            # Обновляем КЭШ всеми свежими данными
            preview_data = {
                "id": str(post_dto.id),
                "title": post_dto.title,
                "author_id": str(post_dto.author_id),
                "author_username": post_dto.author_username,
                "tags": [t.model_dump(mode="json") for t in post_dto.tags],
                "created_at": post_dto.created_at.isoformat(),
                "views_count": post_dto.views_count
            }
            body_data = {
                "body": post_dto.body,
                "attachments": [a.model_dump(mode="json") for a in post_dto.attachments]
            }


            # Фильтруем реакции: оставляем только те, где количество > 0
            active_reactions = {k.value: v for k, v in post_dto.reactions.items() if v > 0}
            
            async with self.cache_redis.pipeline(transaction=True) as pipe:
                
                pipe.set(self.cache_post_preview_key.format(post_id=post_id_str), 
                         json.dumps(preview_data),
                         ex=self.cache_post_preview_ttl)
                pipe.set(self.cache_post_body_key.format(post_id=post_id_str),
                         json.dumps(body_data),
                         ex=self.cache_post_body_ttl)
                pipe.set(self.cache_post_commentsCount_key.format(post_id=post_id_str), 
                         post_dto.comments_count,
                         ex=self.cache_post_commentsCount_ttl)
                
                # реакции на пост
                # Сначала всегда удаляем старый хэш реакций (на случай если все реакции сбросились в 0)
                pipe.delete(self.cache_post_reactions_key.format(post_id=post_id_str))
                
                if active_reactions:
                    pipe.hset(self.cache_post_reactions_key.format(post_id=post_id_str), 
                              mapping=active_reactions)
                else:
                    # Если реакций нет вовсе, создаем маркер-флаг "EMPTY", 
                    # чтобы при следующем запросе знать: реакций нет и в БД идти НЕ нужно
                    pipe.hset(self.cache_post_reactions_key.format(post_id=post_id_str), 
                              mapping={"_state": "EMPTY"})
                
                pipe.expire(self.cache_post_reactions_key.format(post_id=post_id_str), 
                            self.cache_post_reactions_ttl)
                
                # Запоминаем реакцию авторизованного пользователя
                if user_id:
                    u_react = post_dto.user_reaction.value if post_dto.user_reaction else "NONE"
                    pipe.set(self.cache_post_user_reaction_key.format(post_id=post_id_str,
                                                                      user_id=user_id), 
                             u_react,
                             ex=600)

                await pipe.execute()
                
            default_logger.debug("Getting post: post added to cache")
                
            # Инкрементируем просмотры в Redis (для Celery задачи)
            await self.cache_redis.hincrby(self.cache_posts_views, 
                                           post_id_str, 
                                           1)

            return post_dto


        # пост есть в кеше
        # проверяем отдельно комментарии и реакции в кеше
        default_logger.debug("Getting post: getting post from cache")
        
        preview = json.loads(raw_preview)
        body = json.loads(raw_body)

        # 1. Точечная проверка: Кол-во комментариев
        if raw_comments is None:
            default_logger.debug("Getting post: getting comments count from db")
            
            comments_count = await self.post_repo.get_post_comments_count(post_id)
            await self.cache_redis.set(key=self.cache_post_commentsCount_key.format(post_id=post_id_str), 
                                       value=comments_count, 
                                       ttl_seconds=self.cache_post_commentsCount_ttl)
        else:
            comments_count = int(raw_comments)

        # 2. Точечная проверка: Агрегированные реакции поста
        if not raw_reactions:
            default_logger.debug("Getting post: getting reactions from db")
            
            # Запрашиваем реакции из БД через репозиторий
            reactions_from_db = await self.post_repo.get_all_post_reactions(post_id)
            
            # Фильтруем ненулевые
            active_reactions = {k.value: v for k, v in reactions_from_db.items() if v > 0}
            
            await self.cache_redis.delete(self.cache_post_reactions_key.format(post_id=post_id_str))
            if active_reactions:
                await self.cache_redis.hset(self.cache_post_reactions_key.format(post_id=post_id_str), 
                                            mapping=active_reactions)
            else:
                await self.cache_redis.hset(self.cache_post_reactions_key.format(post_id=post_id_str),
                                            mapping={"_state": "EMPTY"})
            
            await self.cache_redis.expire(self.cache_post_reactions_key.format(post_id=post_id_str), 
                                          self.cache_post_reactions_ttl)
            
            # Формируем полный словарь (все типы реакций с дефолтными 0)
            reactions = {r_type: reactions_from_db.get(r_type, 0) for r_type in TypeReactionEnum}

        else:
            default_logger.debug("Getting post: getting reactions from cache")
            
            raw_dict = raw_reactions
            
            # Инициализируем словарь со всеми нулями
            reactions = {r_type: 0 for r_type in TypeReactionEnum}
            
            # Заполняем только те, что реально есть в Redis (игнорируя технический ключ "_state")
            for r_type in TypeReactionEnum:
                if r_type.value in raw_dict and raw_dict[r_type.value] != "EMPTY":
                    reactions[r_type] = int(raw_dict[r_type.value])

        # 3. Точечная проверка: Реакция ТЕКУЩЕГО пользователя
        user_reaction = None
        if user_id:
            if raw_user_reaction is None:
                default_logger.debug("Getting post: getting user reaction from db")
                
                # Если реакции юзера нет в Redis — делаем быстрый запрос в БД за 1 реакцией
                user_reaction = await self.post_repo.get_user_reaction(post_id, user_id)
                u_react_str = user_reaction.value if user_reaction else "NONE"
                await self.cache_redis.set(key=self.cache_post_user_reaction_key.format(
                                                                            post_id=post_id_str,
                                                                            user_id=user_id), 
                                           value=u_react_str, 
                                           ttl_seconds=self.cache_post_user_reaction_ttl,
                                           is_value_serialize=False)
            else:
                default_logger.debug("Getting post: getting user reaction from cache")
                
                val = raw_user_reaction
                user_reaction = TypeReactionEnum(val) if (val and val != "NONE") else None

        # 4. Просмотры
        redis_views = await self.cache_redis.hget(self.cache_posts_views, 
                                                  post_id_str)
        total_views = preview.get("views_count", 0) + (int(redis_views) if redis_views else 0)
        
        default_logger.debug("Getting post: post got from cache")
        
        # Инкрементируем просмотры в Redis (для Celery задачи)
        await self.cache_redis.hincrby(self.cache_posts_views, 
                                       post_id_str, 
                                       1)

        # Возвращаем полный DTO
        return PostFullDTO(
            id=UUID(preview["id"]),
            title=preview["title"],
            body=body["body"],
            attachments=body["attachments"],
            author_id=UUID(preview["author_id"]),
            author_username=preview["author_username"],
            tags=preview["tags"],
            created_at=preview["created_at"],
            views_count=total_views,
            comments_count=comments_count,
            reactions=reactions,
            user_reaction=user_reaction
        )
    
    async def add_reaction_to_post(self, 
                    reaction_data: PostAddReactionDTO, 
                    user_id: UUID) -> tuple[TypeReactionEnum | None, TypeReactionEnum | None]:
        
        default_logger.debug("Adding reaction to post: adding to db")
        
        old_reaction, new_reaction = await self.post_repo.add_reaction_to_post(reaction_data, user_id)
        post_id_str = str(reaction_data.post_id)

        default_logger.debug("Adding reaction to post: adding to cache")
        async with self.cache_redis.pipeline(transaction=True) as pipe:
            # Убираем флаговый маркер если он был
            pipe.hdel(self.cache_post_reactions_key.format(post_id=post_id_str), "_state")

            # Если пользователь сменил/удалил старую реакцию
            if old_reaction:
                pipe.hincrby(self.cache_post_reactions_key.format(post_id=post_id_str), 
                             old_reaction.value,
                             -1)
            
            # Если поставил новую реакцию
            if new_reaction:
                pipe.hincrby(self.cache_post_reactions_key.format(post_id=post_id_str), 
                             new_reaction.value, 
                             1)

            # Обновляем персональную реакцию юзера
            user_react_val = new_reaction.value if new_reaction else "NONE"
            pipe.set(self.cache_post_user_reaction_key.format(post_id=post_id_str, 
                                                              user_id=user_id), 
                     user_react_val, 
                     ex=self.cache_post_user_reaction_ttl)
            
            results = await pipe.execute()

        # Чистка нулей: проверяем результаты HINCRBY
        # Если значение реакции стало <= 0, удаляем это поле из хэша Redis
        async with self.cache_redis.pipeline(transaction=True) as pipe:
            # Проверяем хэш после изменений
            current_reactions = await self.cache_redis.hgetall(
                                self.cache_post_reactions_key.format(post_id=post_id_str))
            
            has_active = False
            for k, v in current_reactions.items():
                key_str = k
                val_int = int(v)
                if val_int <= 0:
                    pipe.hdel(self.cache_post_reactions_key.format(post_id=post_id_str), key_str)
                else:
                    has_active = True
            
            # Если после изменений вообще не осталось реакций, возвращаем маркер "_state": "EMPTY"
            if not has_active:
                pipe.hset(self.cache_post_reactions_key.format(post_id=post_id_str), 
                          mapping={"_state": "EMPTY"})
                
            await pipe.execute()

        return old_reaction, new_reaction
    
    async def update_post(self, post_id: UUID, author_id: UUID, post_data: PostPatchDTO) -> PostWithTagsDTO:
        db_post = await self.post_repo.update_post(post_id, author_id, post_data)
        
        post_id_str = str(post_id)
        default_logger.debug("Updating post: deleting post from cache")
        await self.cache_redis.delete(self.cache_post_preview_key.format(post_id=post_id_str))
        await self.cache_redis.delete(self.cache_post_body_key.format(post_id=post_id_str))
        
        # обновляем кеш с тегами если были добавлены новые
        if post_data.tags:
            await self._check_if_new_tag_in_cache(post_data.tags)
        
        return PostWithTagsDTO.model_validate(db_post)
    
    async def get_user_posts(self, username: str, 
                             limit: int, offset: int) -> PostListDTO:
        
        user_posts_key = f"feed:user_posts:{username}:off:{offset}:lim:{limit}"
        cached_user_posts_feed = await self.cache_redis.get(user_posts_key)

        if cached_user_posts_feed:
            feed_data = json.loads(cached_user_posts_feed)
            posts_dto = await self._fetch_previews_by_ids(feed_data["ids"])
            return PostListDTO(total_count=feed_data["total_count"], posts=posts_dto)

        # Иначе запрос в БД
        total_count, posts_data = await self.post_repo.get_user_posts(username, limit, offset)
        
        # Кэшируем превью в Redis
        post_ids = await self._cache_post_previews(posts_data)
        
        # Сохраняем список ID постов пользователя
        await self.cache_redis.set(user_posts_key, 
                                   json.dumps({"total_count": total_count, "ids": post_ids}), 
                                   ttl_seconds=60)

        posts_dto = [
            PostPreviewDTO.model_validate(p).model_copy(update={"comments_count": c, "author_username": u})
            for p, c, u in posts_data
        ]
        return PostListDTO(total_count=total_count, posts=posts_dto)

    async def get_posts_with_tag(self, tagname: str, 
                                 limit: int, offset: int) -> PostListDTO:
        
        tag_key = f"feed:tag:{tagname}:off:{offset}:lim:{limit}"
        cached_tag_feed = await self.cache_redis.get(tag_key)

        if cached_tag_feed:
            feed_data = json.loads(cached_tag_feed)
            posts_dto = await self._fetch_previews_by_ids(feed_data["ids"])
            return PostListDTO(total_count=feed_data["total_count"], posts=posts_dto)

        # Иначе запрос в БД
        total_count, posts_data = await self.post_repo.get_posts_with_tag(tagname, limit, offset)
        
        # Кэшируем превью в Redis
        post_ids = await self._cache_post_previews(posts_data)
        
        # Сохраняем связку ID для тега
        await self.cache_redis.set(tag_key, 
                                   json.dumps({"total_count": total_count, "ids": post_ids}), 
                                   ttl_seconds=60)

        posts_dto = [
            PostPreviewDTO.model_validate(p).model_copy(update={"comments_count": c, "author_username": u})
            for p, c, u in posts_data
        ]
        return PostListDTO(total_count=total_count, posts=posts_dto)
        
    async def get_posts(self, 
            limit: int, offset: int, 
            sort: PostsSortEnum, period: PeriodEnum,
            include: Set[PostLoadRelations] | None = None) -> PostListDTO:
        
        default_logger.debug("Getting posts: checking cache")
        feed_key = f"feed:{sort.value}:{period.value}:off:{offset}:lim:{limit}"

        cached_feed = await self.cache_redis.get(feed_key)

        if cached_feed:
            default_logger.debug("Getting posts: feed hit from cache")
            feed_data = json.loads(cached_feed) if isinstance(cached_feed, str) else cached_feed
            total_count = feed_data["total_count"]
            post_ids = feed_data["ids"]
        else:
            default_logger.debug("Getting posts: feed miss. Querying DB")
            options = self.add_loading_options(include) if include else None
            total_count, posts_data = await self.post_repo.get_posts(limit, offset, sort, period, options)

            # 1. Сохраняем превью всех полученных постов в Redis
            post_ids = await self._cache_post_previews(posts_data)

            # 2. Кэшируем карту ленты (список ID) на 30 секунд
            feed_payload = json.dumps({"total_count": total_count, "ids": post_ids})
            await self.cache_redis.set(key=feed_key, 
                                       value=feed_payload, 
                                       ttl_seconds=30)

            # 3. Возвращаем DTO напрямую (без повторного запроса в Redis)
            posts_dto = [
                PostPreviewDTO
                .model_validate(post_model)
                .model_copy(update={
                    "comments_count": c_count,
                    "author_username": author_username
                })
                for post_model, c_count, author_username in posts_data
            ]
            return PostListDTO(total_count=total_count, posts=posts_dto)

        posts_dto = await self._fetch_previews_by_ids(post_ids, include)
        return PostListDTO(total_count=total_count, posts=posts_dto)

    async def get_all_existing_tags(self,
                                    #limit: int, offset: int,
                                    include: Set[PostLoadRelations] | None = None) -> Sequence[TagDTO]:
        
        tags_cache_key = "tags_list"
        tags_cache_ttl = 60
        
        default_logger.debug("Cheking tags in cache")
        
        tags_cached = await self.cache_redis.get(key=tags_cache_key)
        if tags_cached:
            default_logger.debug("Tags found in cache")
            return [TagDTO.model_validate(tag) for tag in tags_cached]
        
        default_logger.debug("Tags not in cache. Getting tags from db")
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
            
        db_tags = await self.post_repo.get_all_existing_tags(options)
        
        dto_tags = [TagDTO.model_validate(tag_model) for tag_model in db_tags]
        
        default_logger.debug("Adding tags list to cache")
        await self.cache_redis.set(key=tags_cache_key,
                                   value=[tag.model_dump(mode="json") for tag in dto_tags],
                                   ttl_seconds=tags_cache_ttl)
        
        return dto_tags
    
    async def get_all_post_tags(self, post_id: UUID) -> list[TagDTO]:
        
        tags_cached = await self.cache_redis.get(self.cache_tags_list_key)
        if tags_cached:
            default_logger.debug("Getting tags list from cache")
            return [TagDTO.model_validate(tag) for tag in tags_cached]
        
        db_tags = await self.post_repo.get_all_post_tags(post_id)
        dto_tags = [TagDTO.model_validate(tag_model) for tag_model in db_tags]

        default_logger.debug("Adding tags list to cache")
        await self.cache_redis.set(key=self.cache_tags_list_key,
                                   value=[tag.model_dump(mode="json") for tag in dto_tags], 
                                   ttl_seconds=self.cache_tags_list_ttl)
        
        return dto_tags
    
    async def delete_tag(self, tag_name: str) -> None:
        await self.post_repo.delete_tag(tag_name)
        
        default_logger.debug("Deleting tags list from cache")
        await self.cache_redis.delete(key=self.cache_tags_list_key)
    
    async def get_all_post_reactions(self, post_id: UUID) -> dict[TypeReactionEnum, int]:
        return await self.post_repo.get_all_post_reactions(post_id)
    
    async def find_post_by_title(self, seacrhing_title: str,
                                 limit: int, offset: int,
                                 include: Set[PostLoadRelations] | None = None) -> PostListDTO:
        
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
            
        posts_list = PostListDTO(total_count=len(posts), posts=posts)

        return posts_list
    
    async def find_tags_by_name(self, seacrhing_tag: str,
                                include: Set[PostLoadRelations] | None = None) -> Sequence[TagDTO]:
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        db_tags = await self.post_repo.find_tags_by_name(seacrhing_tag, options)
        return [TagDTO.model_validate(tag) for tag in db_tags]
    
    
    def add_loading_options(self, include: Set[PostLoadRelations]) -> Sequence[ORMOption]:
        return [self._LOAD_MAP[rel] for rel in include if rel in self._LOAD_MAP]
    
    async def _check_if_new_tag_in_cache(self, new_tags: list[TagCreateDTO]):
        # если в кеше нету тегов, ничего не делаем
        tags_cached = await self.cache_redis.get(self.cache_tags_list_key)
        if tags_cached is None:
            return
        
        # если есть, ищем новые в списке (у которого id=None), 
        # если хотя бы один есть - очищаем кеш
        for tag in new_tags:
            if tag.id is None:
                await self.cache_redis.delete(self.cache_tags_list_key)
                return
        
    async def _cache_post_previews(self, posts_data: Sequence[tuple[Any, int, str]]) -> list[str]:
        """
        Кэширует превью постов и кол-во комментариев.
        Возвращает список string UUID постов.
        """
        
        post_ids = []
        async with self.cache_redis.pipeline(transaction=True) as pipe:
            for post_model, comments_count, author_username in posts_data:
                p_id_str = str(post_model.id)
                post_ids.append(p_id_str)

                preview_dict = {
                    "id": p_id_str,
                    "title": post_model.title,
                    "author_id": str(post_model.author_id),
                    "author_username": author_username,
                    "tags": [TagDTO.model_validate(t).model_dump(mode="json") for t in post_model.tags],
                    "views_count": post_model.views_count,
                    "created_at": post_model.created_at.isoformat(),
                }
                pipe.set(self.cache_post_preview_key.format(post_id=p_id_str), 
                         json.dumps(preview_dict),
                         ex=86400)
                pipe.set(self.cache_post_commentsCount_key.format(post_id=p_id_str), 
                         comments_count, 
                         ex=86400)

            await pipe.execute()
        return post_ids

    async def _fetch_previews_by_ids(self, 
                        post_ids: list[str], 
                        include: Set[PostLoadRelations] | None = None) -> list[PostPreviewDTO]:
        """
        Достает превью постов из кэша по спискам ID.
        Если какие-то превью выпали из кэша — дозагружает их пакетом из БД и докэширует.
        Игнорирует посты, которые были удалены из БД.
        """
        
        if not post_ids:
            return []

        preview_keys = [f"post:{pid}:preview" for pid in post_ids]
        comment_keys = [f"post:{pid}:comments_count" for pid in post_ids]

        async with self.cache_redis.pipeline(transaction=False) as pipe:
            pipe.mget(preview_keys)
            pipe.mget(comment_keys)
            pipe_res = await pipe.execute()

        raw_previews, raw_comments = pipe_res[0], pipe_res[1]

        # Определяем ID постов, превью которых отсутствует в кэше
        missing_pids = [UUID(post_ids[i]) for i, raw_p in enumerate(raw_previews) if not raw_p]

        missing_posts_map: dict[str, PostPreviewDTO] = {}
        if missing_pids:
            default_logger.debug("Fetching previews: restoring missing posts from DB")
            options = self.add_loading_options(include) if include else None
            db_missing = await self.post_repo.get_posts_by_ids(missing_pids, options)

            # Сохраняем найденные в БД посты обратно в кэш
            if db_missing:
                await self._cache_post_previews(db_missing)

            # Собираем DTO только для тех постов, которые реально нашлись в БД
            for post_model, comments_count, author_username in db_missing:
                p_id_str = str(post_model.id)
                missing_posts_map[p_id_str] = (
                    PostPreviewDTO
                    .model_validate(post_model)
                    .model_copy(update={
                        "comments_count": comments_count,
                        "author_username": author_username
                    })
                )

        # Собираем финальный порядок списка DTO
        posts_dto = []
        for i, pid in enumerate(post_ids):
            raw_p = raw_previews[i]
            
            # 1. Если поста не было в кэше
            if not raw_p:
                # Если пост нашелся в БД при дозагрузке — добавляем его
                if pid in missing_posts_map:
                    posts_dto.append(missing_posts_map[pid])
                # Если поста нет и в БД (был удален) — просто пропускаем его!
                continue

            # 2. Если пост был в кэше — парсим JSON
            p_data = json.loads(raw_p)
            c_count = int(raw_comments[i]) if raw_comments[i] else 0
            posts_dto.append(
                PostPreviewDTO(
                    id=UUID(p_data["id"]),
                    author_id=UUID(p_data["author_id"]),
                    title=p_data["title"],
                    views_count=p_data.get("views_count", 0),
                    comments_count=c_count,
                    tags=p_data["tags"]
                )
            )

        return posts_dto