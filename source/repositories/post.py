from typing import Sequence, cast, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, delete, and_, func, text, bindparam, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, defer, joinedload
from sqlalchemy.orm.interfaces import ORMOption
from sqlalchemy.sql.elements import BindParameter
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.exc import IntegrityError

from source.models.post import PostModel
from source.models.user import UserModel
from source.models.tag import TagModel
from source.models.attachment_media import AttachmentMediaModel
from source.models.post_reaction import PostReactionModel
from source.models.comment import CommentModel
from source.api.v1.schemas.post import (PostAddDTO, 
                                 PostPatchDTO, 
                                 PostAddReactionDTO)
from source.services.storage.baseStorage import BaseStorage
from source.core.exceptions import (PostNotFoundException,
                                    FileNotFoundException,
                                    TagNotFoundException,
                                    CommittingException)
from source.core.logger import default_logger
from source.core.types import TypeReactionEnum, post_language
from source.core.types import PostsSortEnum, PeriodEnum




class PostRepository:
    
    def __init__(self, db_session: AsyncSession, storage: BaseStorage | None = None):
        self.db_session = db_session
        self.storage = storage
        
    async def make_commit(self):
        await self.db_session.commit()
        
    async def add_post(self, new_post: PostAddDTO, author_id: UUID) -> PostModel:

        post_model = PostModel(author_id=author_id, # связь User<->Post сама построится
                               title=new_post.title,
                               body=new_post.body)
        
        # tags
        if new_post.tags:
            existing_ids = [tag.id for tag in new_post.tags if tag.id is not None]

            existing_tags = {}
            if existing_ids:
                res = await self.db_session.execute(select(TagModel).where(TagModel.id.in_(existing_ids)))
                existing_tags = {tag.id: tag for tag in res.scalars()}

            for tag in new_post.tags:
                if tag.id is not None:
                    tag_model = existing_tags.get(tag.id)
                    if tag_model is None:
                        raise TagNotFoundException(tag.id)

                    post_model.tags.append(tag_model)
                else:
                    post_model.tags.append(TagModel(name=tag.name))
        
        
        default_logger.debug("Adding new post: add post to db")
        # алхимия сама добавит новые теги в базу
        self.db_session.add(post_model)
        
        # attachment files
        if new_post.files_id:
            default_logger.debug("Adding new post: loading media files")
            await self.db_session.flush()
            query = (select(AttachmentMediaModel)
                     .where(and_(AttachmentMediaModel.id.in_(new_post.files_id),
                                 AttachmentMediaModel.user_id == author_id,
                                 AttachmentMediaModel.is_temporary.is_(True),
                                 AttachmentMediaModel.post_id.is_(None),
                                 AttachmentMediaModel.comment_id.is_(None))))
            attachment_res = await self.db_session.execute(query)
            attachments = attachment_res.scalars().all()
            
            if not attachments:
                default_logger.error("Adding new post: Error. Uploaded media files not found in db")
                raise FileNotFoundException("media files not found in db")
            if len(attachments) != len(new_post.files_id):
                default_logger.error("Adding new post: Error. files in db and files in request dont match")
                raise FileNotFoundException("Amount of files dont match")
            
            for attachment in attachments:
                attachment.post_id = post_model.id
                attachment.is_temporary = False
            
            default_logger.debug("Adding new post: files added")
        
        try:
            default_logger.debug("Adding new post: try commit")
            await self.db_session.commit()
        except IntegrityError as e:
            default_logger.error(f"Adding new post: Error. {e}")
            raise CommittingException("Error while saving post")
        
        # подгружаем теги, автора и файлы
        await self.db_session.refresh(post_model, attribute_names=["tags", "attachments", "author"])
        
        return post_model
    
    async def delete_post(self, post_id: UUID, author_id: UUID):
        query = (delete(PostModel)
                 .where(and_(PostModel.id==post_id, PostModel.author_id==author_id))
                 .returning(PostModel.id))
        result = await self.db_session.execute(query)
        deleted_id = result.scalar_one_or_none()
        if deleted_id is None:
            default_logger.error(f"Deleting post. Error. Post not found or user is not author")
            raise PostNotFoundException("Post not found or you dont have permissions to delete this post")
        await self.db_session.commit()
    
    async def delete_tag(self, tag_name: str) -> None:
        query = (delete(TagModel)
                 .where(TagModel.name==tag_name)
                 .returning(TagModel.id))
        result = await self.db_session.execute(query)
        deleted_id = result.scalar_one_or_none()
        if deleted_id is None:
            default_logger.error(f"Deleting tag. Error. Tag {tag_name} not found")
            raise TagNotFoundException("Tag not found")
        await self.db_session.commit()
    
    async def get_post_by_id(self, post_id: UUID, 
                             load_options: Sequence[ORMOption] | None = None) -> PostModel:
        
        default_logger.debug("Getting post from db by id")

        query = select(PostModel).where(PostModel.id==post_id)
        
        if load_options:
            query = query.options(*load_options)
        
        res = await self.db_session.execute(query)
        
        post =  res.scalar_one_or_none()
            
        if post is None:
            default_logger.debug("Getting post from db: Error. Post not found")
            raise PostNotFoundException("Post not found in db")
        
        return post
    
    # получить весь пост с количество комментаиев, автором, реакией текущего пользователя
    async def get_post_with_data(self, 
            user_id: UUID | None,
            post_id: UUID, 
            load_options: Sequence[ORMOption] | None = None) -> tuple[PostModel, 
                                                                      int, 
                                                                      str, 
                                                                      TypeReactionEnum | None]:
    
        # возвращает: пост и доп. колонки - к-во комментов, автор поста, реакция текущего пользователя
        
        default_logger.debug("Getting post with comments count")

        subq_comments_count = (select(func.count(CommentModel.id))
                            .where(CommentModel.post_id == PostModel.id)
                            .scalar_subquery())
        query = (select(PostModel, 
                        subq_comments_count.label("comments_count"),
                        UserModel.username.label("author_username"),
                        PostReactionModel.reaction_type.label("user_reaction"))
                 # автор поста
                .join(UserModel, PostModel.author_id == UserModel.id)
                # реакция пользователя на этот пост
                .outerjoin(PostReactionModel, and_(PostReactionModel.post_id == PostModel.id,
                                                   PostReactionModel.user_id == user_id))
                .where(PostModel.id==post_id))
        
        if load_options:
            query = query.options(*load_options)
        
        res = await self.db_session.execute(query)
        
        post = res.first()
            
        if post is None:
            default_logger.debug("Getting post with comments count: Error. Post not found")
            raise PostNotFoundException("Post not found in db")
        
        return cast(tuple[PostModel, int, str, TypeReactionEnum | None], post)
    
    # увеличить количество просмотров у всех переданных постов
    async def bulk_increment_views(self, updates: list[tuple[UUID, int]]) -> None:
        
        print(f"Post repo session id={id(self.db_session)}")
        
        default_logger.debug("Updating views count: Trying")
        if not updates:
            default_logger.debug("Updating views count: nothing to update")
            return

        default_logger.debug("Updating views count: creating query")

        values = []
        params: dict[str, Any] = {}
        bind_params: list[BindParameter[Any]] = []
        
        for i, (post_id, inc) in enumerate(updates):
            values.append(f"(:id{i}, :inc{i})")
            params[f"id{i}"] = post_id
            params[f"inc{i}"] = inc
            
            bind_params.extend(
            [
                bindparam(f"id{i}", type_=PG_UUID(as_uuid=True)),
                bindparam(f"inc{i}", type_=Integer)
            ])

        query = text(f"""
        UPDATE posts AS p
        SET views_count = p.views_count + v.inc
        FROM (
            VALUES {", ".join(values)}
        ) AS v(id, inc)
        WHERE p.id = v.id
        """).bindparams(*bind_params)

        default_logger.debug("Updating views count: executing query")
        await self.db_session.execute(query, params)
        default_logger.debug("Updating views count: query executed successfuly")
        # commit в другом месте делаем
    
    # список постов (превью) пользователя
    async def get_user_posts(self, username: str,
                             limit: int, offset: int) -> tuple[int, Sequence[tuple[PostModel, 
                                                                                   int,
                                                                                   str]]]:
        
        # 1. Подзапрос для подсчета общего количества постов пользователя (для пагинации)
        total_posts_subq = (
            select(func.count(PostModel.id))
            .join(PostModel.author)
            .where(UserModel.username == username)
            .scalar_subquery()
        )

        # 2. Подзапрос для подсчета комментариев к каждому отдельному посту
        comments_count_subq = (
            select(func.count(CommentModel.id))
            .where(CommentModel.post_id == PostModel.id)
            .scalar_subquery()
        )

        # 3. Основной запрос: получаем пост, количество комментариев к нему и общее число постов
        stmt = (
            select(
                total_posts_subq.label("all_user_posts_count"),
                PostModel,
                comments_count_subq.label("comments_count"),
            )
            .join(PostModel.author)
            .where(UserModel.username == username)
            .order_by(PostModel.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(PostModel.tags))
        )

        result = await self.db_session.execute(stmt)
        rows = result.all()

        if not rows:
            default_logger.info("Getting user posts: posts not found")
            return 0, []

        # Общее количество постов одинаково для всех строк выборки, берем из первой
        total_count = rows[0].all_user_posts_count

        # Формируем список пар: (post_model, comments_count)
        posts_data = [
            (row.PostModel, row.comments_count, username) 
            for row in rows
        ]
        
        return cast(tuple[int, list[tuple[PostModel, int, str]]], (total_count, posts_data))
        
    # список постов без тела (превью) с указанным тегом
    async def get_posts_with_tag(self, 
                                 tagname: str,
                                 limit: int, offset: int) -> tuple[int, Sequence[tuple[PostModel, 
                                                                                       int,
                                                                                       str]]]:
        
        # 1. Подзапрос для подсчета общего количества постов с этим тегом (для пагинации)
        total_posts_with_tag_subq = (
            select(func.count(PostModel.id))
            .join(PostModel.tags)
            .where(TagModel.name.ilike(f"%{tagname}%"))
            .scalar_subquery()
        )

        # 2. Подзапрос для подсчета комментариев к каждому отдельному посту
        comments_count_subq = (
            select(func.count(CommentModel.id))
            .where(CommentModel.post_id == PostModel.id)
            .scalar_subquery()
        )

        # 3. Основной запрос: получаем пост, количество комментариев к нему и общее число постов
        stmt = (
            select(
                total_posts_with_tag_subq.label("total_posts_count"),
                PostModel,
                comments_count_subq.label("comments_count"),
                UserModel.username.label("author_username")
            )
            .join(PostModel.tags)
            .join(UserModel, PostModel.author_id == UserModel.id)
            .where(TagModel.name.ilike(f"%{tagname}%"))
            .order_by(PostModel.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(PostModel.tags))
        )

        result = await self.db_session.execute(stmt)
        rows = result.all()

        if not rows:
            default_logger.info("Getting posts with tag: posts not found")
            return 0, []

        # Общее количество постов одинаково для всех строк выборки, берем из первой
        total_count = rows[0].total_posts_count
        
        default_logger.debug(f"Getting posts with tag: found {total_count} posts")

        # Формируем список: (post_model, comments_count, author_username)
        posts_data = [
            (row.PostModel, row.comments_count, row.author_username) 
            for row in rows
        ]
        
        return cast(tuple[int, list[tuple[PostModel, int, str]]], (total_count, posts_data))

    # список постов без тела (превью)
    async def get_posts(self, 
            limit: int, offset: int,
            sort: PostsSortEnum, period: PeriodEnum,
            load_options: Sequence[ORMOption] | None = None) -> tuple[int, 
                                                                      Sequence[tuple[PostModel, 
                                                                                     int,
                                                                                     str]]]:
        # return: (total_count_posts, list[post, comments_count, author_username])
        
        
        default_logger.debug(f"Getting posts from db: limit={limit}, offset={offset}")
        
        # Собираем условия фильтрации
        where_conditions = []

        if sort == PostsSortEnum.POPULAR and period != PeriodEnum.ALL_TIME:
            now = datetime.now()
            period_deltas = {
                PeriodEnum.DAY: timedelta(days=1),
                PeriodEnum.WEEK: timedelta(weeks=1),
                PeriodEnum.MONTH: timedelta(days=30),
                PeriodEnum.YEAR: timedelta(days=365),
            }
            if period in period_deltas:
                where_conditions.append(PostModel.created_at >= now - period_deltas[period])

        # 1. Подсчет общего количества (Чистый count без связей)
        count_query = select(func.count(PostModel.id)).where(*where_conditions)
        total_count = (await self.db_session.execute(count_query)).scalar_one()

        # 2. Подзапрос количества комментариев
        subq_comments_count = (
            select(func.count(CommentModel.id))
            .where(CommentModel.post_id == PostModel.id)
            .scalar_subquery()
        )

        # 3. Основная выборка
        query = (
            select(
                PostModel,
                subq_comments_count.label("comments_count"),
                UserModel.username.label("author_username")
            )
            .where(*where_conditions)
            .join(UserModel, PostModel.author_id == UserModel.id)
            .options(defer(PostModel.body))
        )

        # Сортировка
        if sort == PostsSortEnum.NEW:
            query = query.order_by(PostModel.created_at.desc())
        elif sort == PostsSortEnum.POPULAR:
            query = query.order_by(PostModel.views_count.desc())

        # Пагинация и доп. опции загрузки
        query = query.limit(limit).offset(offset)
        if load_options:
            query = query.options(*load_options)

        result = await self.db_session.execute(query)
        posts = result.all()

        return cast(tuple[int, list[tuple[PostModel, int, str]]], (total_count, posts))

    async def get_posts_by_ids(self, 
                post_ids: Sequence[UUID], 
                load_options: Sequence[ORMOption] | None = None) -> Sequence[tuple[PostModel, 
                                                                                   int,
                                                                                   str]]:
        
        default_logger.debug(f"Getting {len(post_ids)} posts by ids from db")
        
        subq_comments_count = (
            select(func.count(CommentModel.id))
            .where(CommentModel.post_id == PostModel.id)
            .scalar_subquery()
        )

        query = (select(PostModel,
                        subq_comments_count.label("comments_count"),
                        UserModel.username.label("author_username"))
                 .options(defer(PostModel.body))
                 .join(UserModel, PostModel.author_id == UserModel.id)
                 .where(PostModel.id.in_(post_ids)))

        if load_options:
            query = query.options(*load_options)

        result = await self.db_session.execute(query)
        posts = result.all()
        
        return cast(list[tuple[PostModel, int, str]], posts)
        
    async def update_post(self, post_id: UUID, author_id: UUID, post_data: PostPatchDTO) -> PostModel:
        default_logger.debug("Updating post: start")
        
        # словарь с только указанными полями в запросе
        only_updated_data = post_data.model_dump(exclude_unset=True)
        
        if not only_updated_data:
            default_logger.debug("Updating post: nothing to update")
            # все поля пустые
            # ничего не меняем
            # возвращаем этот пост
            options = [selectinload(PostModel.tags), 
                       selectinload(PostModel.attachments),
                       joinedload(PostModel.author)]
            return await self.get_post_by_id(post_id, options)
        
        # теги и файлы обновим потом отдельно
        updated_tags = only_updated_data.pop("tags", None)
        updated_files_id = only_updated_data.pop("files_id", None)
        
        # достаем пост из базы (с тегами и файлами)
        default_logger.debug("Updating post: getting post from db")
        query = (select(PostModel)
                 .where(and_(PostModel.id==post_id, PostModel.author_id==author_id))
                 .options(selectinload(PostModel.tags), selectinload(PostModel.attachments)))
        result = await self.db_session.execute(query)
        post_model = result.scalar_one_or_none()
        if post_model is None:
            default_logger.error(f"Updating post. Error. Post not found or user is not author")
            raise PostNotFoundException("Post not found or you dont have permissions to update this post")
            
        # обновляем переданные поля
        default_logger.debug("Updating post: updating post columns")
        for key, value in only_updated_data.items():
            setattr(post_model, key, value)
        
        # обновляем теги
        if updated_tags is not None:
            
            if len(updated_tags) == 0:
                default_logger.debug("Updating post: deleting all tags from post")
                post_model.tags = []
            else:
                default_logger.debug("Updating post: updating post tags")
                
                existing_ids = [tag["id"] for tag in updated_tags if tag.get("id", None)]

                existing_tags = {}
                if existing_ids:
                    res = await self.db_session.execute(select(TagModel).where(TagModel.id.in_(existing_ids)))
                    existing_tags = {tag.id: tag for tag in res.scalars()}
                    
                # удаляем все старые теги с поста
                post_model.tags = []

                for tag in updated_tags:
                    if tag.get("id", None):
                        tag_model = existing_tags.get(tag["id"])
                        if tag_model is None:
                            raise TagNotFoundException(tag["id"])

                        post_model.tags.append(tag_model)
                    else:
                        post_model.tags.append(TagModel(name=tag["name"]))
                        
                default_logger.error("Updating post: all tags updated")
                self.db_session.add(post_model)
        
        # обновляем файлы
        filenames_to_delete = []
        if updated_files_id is not None:
            default_logger.debug("Updating post: updating attachments")
            
            # Конвертируем пришедшие ID в UUID для корректного сравнения
            target_ids = {UUID(f_id) if isinstance(f_id, str) else f_id for f_id in updated_files_id}
            current_attachments = {att.id: att for att in post_model.attachments}
            current_ids = set(current_attachments.keys())
            
            # Определяем, какие файлы нужно удалить (они есть в модели, но их нет в запросе)
            ids_to_remove = current_ids - target_ids
            # Определяем, какие файлы нужно добавить (они есть в запросе, но их нет в модели)
            ids_to_add = target_ids - current_ids
            
            # Удаляем старые файлы
            if ids_to_remove:
                default_logger.debug(f"Updating post: removing {len(ids_to_remove)} files")
                for file_id in ids_to_remove:
                    file_to_delete = current_attachments[file_id]
                    # Если у тебя настроен каскад delete-orphan, удаление из списка удалит запись из БД
                    post_model.attachments.remove(file_to_delete)
                    
                    filenames_to_delete.append(file_to_delete.filename)
            
            # Добавляем новые файлы
            if ids_to_add:
                default_logger.debug(f"Updating post: loading {len(ids_to_add)} new media files")
                
                query_files = (
                    select(AttachmentMediaModel)
                    .where(and_(
                        AttachmentMediaModel.id.in_(ids_to_add),
                        AttachmentMediaModel.user_id == author_id,
                        AttachmentMediaModel.is_temporary.is_(True),
                        AttachmentMediaModel.post_id.is_(None)
                    ))
                )
                attachments_res = await self.db_session.execute(query_files)
                new_attachments = attachments_res.scalars().all()
                
                if len(new_attachments) != len(ids_to_add):
                    default_logger.error("Updating post: Error. New media files not found or access denied")
                    raise FileNotFoundException("Some uploaded media files were not found or invalid")
                
                for attachment in new_attachments:
                    attachment.is_temporary = False
                    attachment.post_id = post_id
                    post_model.attachments.append(attachment)
        
        default_logger.debug("Updating post: saving")
        # сохраняем
        try:
            await self.db_session.commit()
        except:
            raise CommittingException("error while saving post")
            
        await self.db_session.refresh(post_model, attribute_names=["tags", "attachments", "author"])
        
        # удаляем файлы с хранилища если такие есть
        if filenames_to_delete:
            default_logger.debug("Updating post: delete files from storage")
            for filename in filenames_to_delete:
                if self.storage:
                    self.storage.delete(filename)
                else:
                    default_logger.error("Updating post: cant delete files. storage isn't set")
        
        return post_model

    async def add_reaction_to_post(self, 
                    reaction_data: PostAddReactionDTO, 
                    user_id: UUID) -> tuple[TypeReactionEnum | None, TypeReactionEnum | None]:
        # return: (old reaction, new reaction)
        
        default_logger.debug("Adding reaction to post: check if post exists")
        post = await self.get_post_by_id(reaction_data.post_id)
        # если поста нету, будет raise error
        
        default_logger.debug("Adding reaction to post: check if user already reacted to this post")
        query = (select(PostReactionModel)
                .where(and_(PostReactionModel.user_id==user_id,
                            PostReactionModel.post_id==reaction_data.post_id)))
        res = await self.db_session.execute(query)
        reaction = res.scalar_one_or_none()
        
        old_reaction: TypeReactionEnum | None = None
        new_reaction: TypeReactionEnum | None = None
        
        if reaction and reaction.reaction_type == reaction_data.reaction_type:
            default_logger.debug("Adding reaction to post: user made same reaction. delete his reaction")
            
            old_reaction = reaction.reaction_type
            
            await self.db_session.delete(reaction)
        
        elif reaction and reaction.reaction_type != reaction_data.reaction_type:
            default_logger.debug("Adding reaction to post: user changed reaction to post")
            
            old_reaction = reaction.reaction_type
            new_reaction = reaction_data.reaction_type 
            
            reaction.reaction_type = reaction_data.reaction_type
            
        else:
            default_logger.debug("Adding reaction to post: user adding new reaction to post")
            reaction_model = PostReactionModel(user_id=user_id,
                                               post_id=reaction_data.post_id,
                                               reaction_type=reaction_data.reaction_type)
            self.db_session.add(reaction_model)
            
            new_reaction = reaction_data.reaction_type
        
        await self.db_session.commit()
        default_logger.info("Adding reaction to post: reaction added")
        
        return (old_reaction, new_reaction)
    
    # все существующие теги
    async def get_all_existing_tags(self,
                                    #limit: int, offset: int,
                                    load_options: Sequence[ORMOption] | None = None) -> Sequence[TagModel]:
        #query = (select(TagModel).limit(limit).offset(offset))
        query = (select(TagModel)
                 .order_by(TagModel.name.asc()))
        
        if load_options:
            query = query.options(*load_options)
        res = await self.db_session.execute(query)
        return res.scalars().all()
       
    # все теги поста 
    async def get_all_post_tags(self, post_id: UUID) -> list[TagModel]:
        query = (select(PostModel)
                 .where(PostModel.id==post_id)
                 .options(selectinload(PostModel.tags)))
        res = await self.db_session.execute(query)
        post = res.scalar_one_or_none()
        if post is None:
            raise PostNotFoundException("Post not found")
        
        return post.tags
    
    # все реакции под постом
    async def get_all_post_reactions(self, post_id: UUID) -> dict[TypeReactionEnum, int]:
        query = (select(PostModel)
                 .where(PostModel.id==post_id)
                 .options(selectinload(PostModel.reactions_list)))
        res = await self.db_session.execute(query)
        post = res.scalar_one_or_none()
        if post is None:
            raise PostNotFoundException("Post not found")
        
        return post.reactions
    
    # количество комментариев под постом
    async def get_post_comments_count(self, post_id: UUID) -> int:
        query = (select(func.count(CommentModel.id))
                 .where(CommentModel.post_id == post_id))
        res = await self.db_session.execute(query)
        return res.scalar_one()
    
    # получить оставленную реакцию пользователя
    async def get_user_reaction(self, post_id: UUID, user_id: UUID) -> TypeReactionEnum | None:
        query = (select(PostReactionModel.reaction_type)
                 .where(PostReactionModel.post_id == post_id,
                        PostReactionModel.user_id == user_id))
        res = await self.db_session.execute(query)
        return res.scalar()
          
    async def find_tags_by_name(self, seacrhing_tag: str,
                                load_options: Sequence[ORMOption] | None = None) -> Sequence[TagModel]:
        query = select(TagModel).where(TagModel.name.ilike(f"%{seacrhing_tag}%"))
        if load_options:
            query = query.options(*load_options)
            
        res = await self.db_session.execute(query)
        return res.scalars().all()
    
    # расширенный поиск статей по названию
    # сначала методом full-text search 
    # (разбивка по словам, лемматизация с указанием языка (то есть приведение слов к общей основе))
    # если ничего не найдет то используем метод триграмм
    #   разбивка слов на 3-буквенные части
    #   метод работает с любым языком и может исправлять ошибки в словах
    async def find_post_by_title(self, seacrhing_title: str,
                                 limit: int, offset: int,
                                 load_options: Sequence[ORMOption] | None = None) -> Sequence[tuple[PostModel, int]]:
        default_logger.debug("Finding posts by title: try to find using full-text search (FTS) method")

        # query = select(PostModel).where(PostModel.title.ilike(f"%{seacrhing_title}%"))
        
        # в методах нужно указать язык чтобы поиск корректно отрабатывал. по умолчанию russian
        # to_tsvector превращает title постов из базы в вектор слов
        # plainto_tsquery превращает переданную строку в поисковый запрос (разбивка на токены через AND)
        # .op("@@") это оператор MATCH для сравнения результатов этих двух методов
        subq_comments_count = (select(func.count(CommentModel.id))
                               .where(CommentModel.post_id == PostModel.id)
                               .scalar_subquery())
        query = (select(PostModel, subq_comments_count.label("comments_count"))
                 .where(func.to_tsvector(post_language, PostModel.title)
                        .op("@@")(func.plainto_tsquery(post_language, seacrhing_title)))
                 .options(defer(PostModel.body))
                 .order_by(PostModel.created_at.desc())
                 .limit(limit)
                 .offset(offset))
        
        if load_options:
            query = query.options(*load_options)
        
        res = await self.db_session.execute(query)
        posts = res.all()
        if not posts:
            default_logger.debug("Finding posts by title: FTS method not found any posts")
            return await self.find_post_by_title_trigramms_method(seacrhing_title, limit, offset,
                                                                  load_options)
        
        return cast(list[tuple[PostModel, int]], posts)
    
    # поиск постов методом триграмм
    async def find_post_by_title_trigramms_method(
                self, 
                seacrhing_title: str,
                limit: int, offset: int,
                load_options: Sequence[ORMOption] | None = None) -> Sequence[tuple[PostModel, int]]:
        
        default_logger.info("Finding posts by title: try to find posts using trigramms")

        # по желанию можно порог схожести. по умолчанию 0.3
        #await self.db_session.execute(text("SET pg_trgm.word_similarity_threshold = 0.2;"))
        await self.db_session.execute(text("SET pg_trgm.similarity_threshold = 0.2;"))

        # Вычисляем схожесть между поисковым запросом и названием статьи
        #similarity = func.word_similarity(seacrhing_title, PostModel.title)
        similarity = func.similarity(PostModel.title, seacrhing_title)
        
        # .op("%") оператор схожести
        # мы сравниваем title из базы и переданную строку
        # оператор возвращает true если схожесть выше порога (0.3 по дефолту)
        subq_comments_count = (select(func.count(CommentModel.id))
                               .where(CommentModel.post_id == PostModel.id)
                               .scalar_subquery())
        query = (select(PostModel, subq_comments_count.label("comments_count"))
                 .where(PostModel.title.op("%")(seacrhing_title))
                 .options(defer(PostModel.body))
                 .order_by(similarity.desc())
                 .limit(limit)
                 .offset(offset))
        
        if load_options:
            query = query.options(*load_options)
        
        res = await self.db_session.execute(query)
        return cast(list[tuple[PostModel, int]], res.all())
    
        # чтобы ускорить поиск для большого количества данных в базе
        # можно добавить для триграмм индекс GiST или GIN