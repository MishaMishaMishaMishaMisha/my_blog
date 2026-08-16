import json

from datetime import datetime
from uuid import UUID
from enum import Enum
from typing import Sequence, Set, Any
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.orm.interfaces import ORMOption

from source.cache.redis_backend import RedisBackend
from source.repositories.comment import CommentRepository
from source.models.comment import CommentModel
from source.api.v1.schemas.comment import CommentAddDTO, CommentPatchDTO, CommentAddReactionDTO
from source.api.v1.schemas.comment import CommentWithReactionsDTO, CommentWithoutRelationsDTO
from source.api.v1.schemas.attachment import AttachmentDTO
from source.core.logger import default_logger
from source.core.types import TypeReactionEnum


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
        
        self.cache_post_commentsCount_key = "post:{post_id}:comments_count"
        self.cache_comment_key = "comment:{comment_id}"
        self.cache_comment_reactions_key = "comment:{comment_id}:reactions"
        self.cache_comment_user_reaction_key = "comment:{comment_id}:user_reaction:{user_id}"
        
        self.cache_post_commentsCount_ttl = 86400 # 1 day
        self.cache_comment_ttl = 86400
        self.cache_comment_reactions_ttl = 86400
        self.cache_comment_user_reaction_ttl = 300 # 5 minutes
        
    async def create_new_comment(self, new_comment: CommentAddDTO, 
                                 author_id: UUID,
                                 post_id: UUID) -> CommentWithoutRelationsDTO: 
        
        if new_comment.parent_id:
            _ = await self.comment_repo.get_comment_by_id(new_comment.parent_id)
            # если parent не найден, будет вызвана ошибка которую отловит router
            # ответ появится через 30 секунд после обновления кеша
               
        db_comment = await self.comment_repo.add_comment(new_comment, author_id, post_id)
        dto_comment = CommentWithoutRelationsDTO.model_validate(db_comment)
        
        comment_id_str = str(dto_comment.id)
        
        default_logger.debug("Adding comment: adding to cache")
        comment_data = {
            "id": comment_id_str,
            "author_id": str(dto_comment.author_id),
            "parent_id": str(dto_comment.parent_id) if dto_comment.parent_id else None,
            "author_username": db_comment.author.username,
            "body": dto_comment.body,
            "attachments": [a.model_dump(mode="json") for a in dto_comment.attachments],
            "created_at": db_comment.created_at.isoformat(),
            "replies_count": 0
        }

        async with self.cache_redis.pipeline(transaction=True) as pipe:
            
            # comment
            pipe.set(self.cache_comment_key.format(comment_id=comment_id_str), 
                     json.dumps(comment_data), 
                     ex=self.cache_comment_ttl)

            # increase comments count of post in cache
            key_coms_count = self.cache_post_commentsCount_key.format(post_id=post_id)
            cur_value = await self.cache_redis.get(key_coms_count)
            ttl = await self.cache_redis.get_expire_key_time(key_coms_count)
            if not cur_value:
                cur_value = 0
                ttl = self.cache_post_commentsCount_ttl
            pipe.set(key_coms_count, cur_value+1, ex=ttl)
            
            # реакции помечаем как empty
            pipe.hset(self.cache_comment_reactions_key.format(comment_id=comment_id_str), 
                          mapping={"_state": "EMPTY"})
            
            await pipe.execute()

        default_logger.debug("Adding comment: comment added to cache")
        
        return dto_comment
    
    async def delete_comment(self, comment_id: UUID, user_id: UUID):
        result = await self.comment_repo.delete_comment(comment_id, user_id)
        
        post_id_str = str(result[1])
        comment_id_str = str(comment_id)
        
        default_logger.debug("Deleting comment from cache")
        # comment
        await self.cache_redis.delete(self.cache_comment_key.format(comment_id=comment_id_str))
        # reactions
        await self.cache_redis.delete(self.cache_comment_reactions_key.format(comment_id=comment_id_str))
        # decrease comments count in cache
        key = self.cache_post_commentsCount_key.format(post_id=post_id_str)
        cur_value = await self.cache_redis.get(key)
        ttl = await self.cache_redis.get_expire_key_time(key)
        if cur_value:
            await self.cache_redis.set(key=key, 
                                       value=cur_value-1, 
                                       ttl_seconds=ttl)
    
    async def get_comment_by_id(self, 
                    comment_id: UUID,
                    include: Set[CommentLoadRelations] | None = None) -> CommentWithReactionsDTO:
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        comment_db = await self.comment_repo.get_comment_by_id(comment_id, options)
        default_logger.debug("Getting comment: comment found")
        
        return CommentWithReactionsDTO.model_validate(comment_db)
    
    async def add_reaction_to_comment(self, 
                    reaction_data: CommentAddReactionDTO, 
                    user_id: UUID) -> tuple[TypeReactionEnum | None, TypeReactionEnum | None]:

        old_reaction, new_reaction = await self.comment_repo.add_reaction_to_comment(reaction_data, 
                                                                                     user_id)
        comment_id_str = str(reaction_data.comment_id)

        default_logger.debug("Adding reaction to comment: adding to cache")
        async with self.cache_redis.pipeline(transaction=True) as pipe:
            # Убираем флаговый маркер если он был
            pipe.hdel(self.cache_comment_reactions_key.format(comment_id=comment_id_str), "_state")

            # Если пользователь сменил/удалил старую реакцию
            if old_reaction:
                pipe.hincrby(self.cache_comment_reactions_key.format(comment_id=comment_id_str), 
                             old_reaction.value,
                             -1)
            
            # Если поставил новую реакцию
            if new_reaction:
                pipe.hincrby(self.cache_comment_reactions_key.format(comment_id=comment_id_str), 
                             new_reaction.value, 
                             1)

            # Обновляем персональную реакцию юзера
            user_react_val = new_reaction.value if new_reaction else "NONE"
            pipe.set(self.cache_comment_user_reaction_key.format(comment_id=comment_id_str, 
                                                                 user_id=user_id), 
                     user_react_val, 
                     ex=self.cache_comment_user_reaction_ttl)
            
            results = await pipe.execute()

        # Чистка нулей: проверяем результаты HINCRBY
        # Если значение реакции стало <= 0, удаляем это поле из хэша Redis
        async with self.cache_redis.pipeline(transaction=True) as pipe:
            # Проверяем хэш после изменений
            current_reactions = await self.cache_redis.hgetall(
                                self.cache_comment_reactions_key.format(comment_id=comment_id_str))
            
            has_active = False
            for k, v in current_reactions.items():
                key_str = k
                val_int = int(v)
                if val_int <= 0:
                    pipe.hdel(self.cache_comment_reactions_key.format(comment_id=comment_id_str), key_str)
                else:
                    has_active = True
            
            # Если после изменений вообще не осталось реакций, возвращаем маркер "_state": "EMPTY"
            if not has_active:
                pipe.hset(self.cache_comment_reactions_key.format(comment_id=comment_id_str), 
                          mapping={"_state": "EMPTY"})
                
            await pipe.execute()

        return old_reaction, new_reaction
    
    async def update_comment(self, 
                             comment_id: UUID, 
                             author_id: UUID, 
                             comment_data: CommentPatchDTO) -> CommentWithoutRelationsDTO:
        
        comment_db = await self.comment_repo.update_comment(comment_id, author_id, comment_data)
        
        comment_id_str = str(comment_id)
        default_logger.debug("Deleting comment from cache")
        await self.cache_redis.delete(self.cache_comment_key.format(comment_id=comment_id_str))
        
        return CommentWithoutRelationsDTO.model_validate(comment_db)
    
    async def get_all_comment_reactions(self, comment_id: UUID) -> dict[TypeReactionEnum, int]:
        return await self.comment_repo.get_all_comment_reactions(comment_id)
    
    async def get_all_post_root_comments(self, 
            user_id: UUID | None,
            post_id: UUID, 
            limit: int, offset: int,
            include: Set[CommentLoadRelations] | None = None) -> Sequence[CommentWithReactionsDTO]:

        default_logger.debug("Getting comments: checking cache")
        comments_list_key = f"post:{post_id}:comments_root:off:{offset}:lim:{limit}"
        
        cached_comments_list = await self.cache_redis.get(comments_list_key)

        if cached_comments_list:
            default_logger.debug("Getting comments: found in cache")
            feed_data = json.loads(cached_comments_list) if isinstance(cached_comments_list, str) else cached_comments_list
            comment_ids = feed_data["ids"]
            return await self._fetch_comments_by_ids(comment_ids, user_id, include)

        default_logger.debug("Getting comments: not in cache. getting from db")
        options = self.add_loading_options(include) if include else None

        comments_data = await self.comment_repo.get_post_root_comments(
            user_id, post_id, limit, offset, options
        )

        default_logger.debug("Getting comments: adding comments to cache")
        # Кэшируем объекты комментариев, их реакции и реакции юзера
        comment_ids = await self._cache_comments_data(user_id, comments_data)

        # Сохраняем список id страницы комментариев на 30 секунд
        comments_list_payload = json.dumps({"ids": comment_ids})
        await self.cache_redis.set(key=comments_list_key, 
                                   value=comments_list_payload, 
                                   ttl_seconds=30)

        # Формируем DTO для немедленного ответа
        comments = []
        for c_model, u_name, replies_cnt, u_react in comments_data:
            reacts_dict = {}
            if hasattr(c_model, "reactions") and c_model.reactions:
                reacts_dict = {
                    TypeReactionEnum(k) if isinstance(k, str) else k: v 
                    for k, v in c_model.reactions.items() if v > 0
                }

            dto = CommentWithReactionsDTO(
                id=c_model.id,
                post_id=c_model.post_id,
                author_id=c_model.author_id,
                parent_id=c_model.parent_id,
                body=c_model.body,
                attachments=[AttachmentDTO.model_validate(a) for a in (c_model.attachments or [])],
                author_username=u_name,
                created_at=c_model.created_at,
                reactions=reacts_dict,
                count_replies=replies_cnt,
                user_reaction=u_react
            )
            comments.append(dto)

        return comments
    
    async def get_comment_root_replies(self, 
                user_id: UUID | None,
                comment_id: UUID, 
                limit: int, offset: int,
                include: Set[CommentLoadRelations] | None = None) -> list[CommentWithReactionsDTO]:

        default_logger.debug("Getting comment replies: checking cache")
 
        replies_list_key = f"comment:{comment_id}:replies:off:{offset}:lim:{limit}"
        cached_replies_list = await self.cache_redis.get(replies_list_key)

        if cached_replies_list:
            default_logger.debug("Getting comment replies: found in cache")
            feed_data = (
                json.loads(cached_replies_list) 
                if isinstance(cached_replies_list, str) 
                else cached_replies_list
            )
            reply_ids = feed_data["ids"]
            # Вычитываем сущности комментариев, их реакции и реакции юзера через пайплайн
            return await self._fetch_comments_by_ids(reply_ids, user_id, include)

        default_logger.debug("Getting comment replies: not in cache. getting from db")
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)

        replies_data = await self.comment_repo.get_comment_root_replies(
            user_id,
            comment_id, 
            limit, 
            offset, 
            options
        )

        default_logger.debug("Getting comment replies: adding replies to cache")

        # 1. Сохраняем сущности самих ответов, их агрегированные реакции и персональную реакцию юзера
        reply_ids = await self._cache_comments_data(user_id, replies_data)

        # 2. Кэшируем список ID этой страницы ответов на 30 секунд
        replies_list_payload = json.dumps({"ids": reply_ids})
        await self.cache_redis.set(key=replies_list_key, 
                                   value=replies_list_payload, 
                                   ttl_seconds=30)

        # 3. Собираем DTO для ответа (как в вашей исходной логике)
        replies = []
        for comment_model, author_username, count_replies, user_reaction in replies_data:
            dto = (
                CommentWithReactionsDTO
                .model_validate(comment_model)
                .model_copy(update={"author_username": author_username})
                .model_copy(update={"count_replies": count_replies})
                .model_copy(update={"user_reaction": user_reaction})
            )
            replies.append(dto)
            
        return replies


    
    def add_loading_options(self, include: Set[CommentLoadRelations]) -> Sequence[ORMOption]:
        return [self._LOAD_MAP[rel] for rel in include if rel in self._LOAD_MAP]
    

    async def _cache_comments_data(
            self,
            user_id: UUID | None,
            comments_data: Sequence[tuple[Any, str, int, TypeReactionEnum | None]]
        ) -> list[str]:
            """
            Сохраняет основные данные комментариев, их счетчики реакций
            и (при наличии user_id) реакцию текущего пользователя.
            """
            if not comments_data:
                return []

            comment_ids = []
            async with self.cache_redis.pipeline(transaction=True) as pipe:
                
                for comment_model, author_username, count_replies, user_reaction in comments_data:
                    c_id_str = str(comment_model.id)
                    comment_ids.append(c_id_str)

                    # 1. Данные комментария
                    comment_dict = {
                        "id": c_id_str,
                        "post_id": str(comment_model.post_id),
                        "author_id": str(comment_model.author_id),
                        "parent_id": str(comment_model.parent_id) if comment_model.parent_id else None,
                        "author_username": author_username,
                        "body": comment_model.body,
                        "attachments": [AttachmentDTO.model_validate(a).model_dump(mode="json") 
                                        for a in comment_model.attachments],
                        "count_replies": count_replies,
                        "created_at": comment_model.created_at.isoformat(),
                    }
                    pipe.set(
                        self.cache_comment_key.format(comment_id=c_id_str),
                        json.dumps(comment_dict),
                        ex=self.cache_comment_ttl
                    )

                    # 2. Агрегированные реакции комментария
                    # comment_model.reactions содержит dict вида {TypeReactionEnum: int}
                    reactions_key = self.cache_comment_reactions_key.format(comment_id=c_id_str)
                    pipe.delete(reactions_key)

                    active_reactions = {}
                    if hasattr(comment_model, "reactions") and comment_model.reactions:
                        active_reactions = {
                            k.value if hasattr(k, "value") else str(k): v 
                            for k, v in comment_model.reactions.items() if v > 0
                        }

                    if active_reactions:
                        pipe.hset(reactions_key, mapping=active_reactions)
                    else:
                        pipe.hset(reactions_key, mapping={"_state": "EMPTY"})
                    pipe.expire(reactions_key, self.cache_comment_reactions_ttl)

                    # 3. Реакция текущего пользователя
                    if user_id:
                        u_react_key = self.cache_comment_user_reaction_key.format(
                            comment_id=c_id_str, user_id=str(user_id)
                        )
                        user_react_val = user_reaction.value if user_reaction else "NONE"
                        pipe.set(u_react_key, user_react_val, ex=self.cache_comment_user_reaction_ttl)

                await pipe.execute()

            return comment_ids


    async def _fetch_comments_by_ids(
            self,
            comment_ids: list[str],
            user_id: UUID | None = None,
            include: Set[CommentLoadRelations] | None = None
        ) -> list[CommentWithReactionsDTO]:
            """
            Пакетно вычитывает комментарии, свод реакций и реакции пользователя из Redis.
            При промахе кэша дозагружает отсутствующие комментарии из БД.
            """
            if not comment_ids:
                return []

            # Формируем ключи для pipeline
            comment_keys = [self.cache_comment_key.format(comment_id=cid) for cid in comment_ids]
            reactions_keys = [self.cache_comment_reactions_key.format(comment_id=cid) for cid in comment_ids]

            async with self.cache_redis.pipeline(transaction=False) as pipe:
                pipe.mget(comment_keys)
                for r_key in reactions_keys:
                    pipe.hgetall(r_key)
                
                if user_id:
                    user_react_keys = [
                        self.cache_comment_user_reaction_key.format(comment_id=cid, user_id=str(user_id))
                        for cid in comment_ids
                    ]
                    pipe.mget(user_react_keys)

                results = await pipe.execute()

            # Разбираем пакетный ответ pipeline
            raw_comments = results[0]
            raw_reactions = results[1:1 + len(comment_ids)]
            raw_user_reactions = results[1 + len(comment_ids)] if user_id else [None] * len(comment_ids)

            # Выявляем выпавшие из кэша комментарии
            missing_ids = [UUID(comment_ids[i]) for i, raw_c in enumerate(raw_comments) if not raw_c]

            missing_map: dict[str, CommentWithReactionsDTO] = {}
            if missing_ids:
                default_logger.debug("Fetching comments: restoring missing items from DB")
                options = self.add_loading_options(include) if include else None
                
                # Репозиторий возвращает: [(CommentModel, author_username, count_replies, user_reaction)]
                db_missing = await self.comment_repo.get_comments_by_ids(missing_ids, user_id, options)

                if db_missing:
                    # Дозаписываем восстановленные комментарии в Redis
                    await self._cache_comments_data(user_id, db_missing)

                    for c_model, u_name, replies_cnt, u_react in db_missing:
                        cid_str = str(c_model.id)
                        
                        # Преобразуем словарь реакций модели в словарь {TypeReactionEnum: int}
                        reacts_dict = {}
                        if hasattr(c_model, "reactions") and c_model.reactions:
                            reacts_dict = {
                                TypeReactionEnum(k) if isinstance(k, str) else k: v 
                                for k, v in c_model.reactions.items() if v > 0
                            }

                        missing_map[cid_str] = CommentWithReactionsDTO(
                            id=c_model.id,
                            post_id=c_model.post_id,
                            author_id=c_model.author_id,
                            parent_id=c_model.parent_id,
                            body=c_model.body,
                            attachments=[AttachmentDTO.model_validate(a) for a in (c_model.attachments or [])],
                            author_username=u_name,
                            created_at=c_model.created_at,
                            reactions=reacts_dict,
                            count_replies=replies_cnt,
                            user_reaction=u_react
                        )

            # Собираем итоговый список с сохранением порядка сортировки
            comments_dto: list[CommentWithReactionsDTO] = []
            for i, cid in enumerate(comment_ids):
                raw_c = raw_comments[i]

                # Если комментария не было в кэше
                if not raw_c:
                    if cid in missing_map:
                        comments_dto.append(missing_map[cid])
                    continue  # Если комментарий был удален из БД, пропускаем

                # Если комментарий найден в кэше
                c_dict = json.loads(raw_c)
                
                # Парсим свод реакций из Redis Hash
                h_reacts = raw_reactions[i] or {}
                reactions_dict: dict[TypeReactionEnum, int] = {}
                for react_type_str, count_str in h_reacts.items():
                    if react_type_str != "_state":
                        reactions_dict[TypeReactionEnum(react_type_str)] = int(count_str)

                # Парсим персональную реакцию пользователя
                user_react_val = raw_user_reactions[i]
                parsed_user_reaction: TypeReactionEnum | None = None
                if user_react_val and user_react_val != "NONE":
                    parsed_user_reaction = TypeReactionEnum(user_react_val)

                dto = CommentWithReactionsDTO(
                    id=UUID(c_dict["id"]),
                    post_id=UUID(c_dict["post_id"]),
                    author_id=UUID(c_dict["author_id"]),
                    parent_id=UUID(c_dict["parent_id"]) if c_dict.get("parent_id") else None,
                    body=c_dict["body"],
                    attachments=[AttachmentDTO.model_validate(a) for a in c_dict.get("attachments", [])],
                    author_username=c_dict.get("author_username", ""),
                    created_at=datetime.fromisoformat(c_dict["created_at"]),
                    reactions=reactions_dict,
                    count_replies=c_dict.get("count_replies", 0),
                    user_reaction=parsed_user_reaction
                )
                comments_dto.append(dto)

            return comments_dto
