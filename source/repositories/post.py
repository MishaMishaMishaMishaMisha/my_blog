from sqlalchemy.ext.asyncio import AsyncSession
from source.models.post import PostModel
from source.models.user import UserModel
from source.models.tag import TagModel
#from source.models.comment import CommentModel
from source.models.attachment_media import AttachmentMediaModel
from source.models.post_reaction import PostReactionModel
from source.models.comment import CommentModel
from source.schemas.post import PostAddDTO, PostPatchDTO, PostAddReactionDTO
from source.services.storage.localStorage import LocalStorage
from sqlalchemy import select, delete, and_, update, func, text, bindparam, Integer
from sqlalchemy.orm import selectinload, defer
from source.core.exceptions import PostNotFoundException, FileNotFoundException
from source.core.logger import default_logger
from typing import Sequence, cast
from uuid import UUID
from source.core.types import TypeReactionEnum, post_language
from sqlalchemy.orm.interfaces import ORMOption
from source.core.types import PostsSortEnum, PeriodEnum
from datetime import datetime, timedelta, UTC
from typing import Any
from sqlalchemy.sql.elements import BindParameter
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class PostRepository:
    
    def __init__(self, db_session: AsyncSession, storage: LocalStorage | None = None):
        self.db_session = db_session
        self.storage = storage
        
    async def make_commit(self):
        await self.db_session.commit()
        
    async def add_post(self, new_post: PostAddDTO, author_id: UUID) -> PostModel:

        post_model = PostModel(author_id=author_id, # связь User<->Post сама построится
                               title=new_post.title,
                               body=new_post.body)
        
        # tags
        if new_post.tags is not None:
            default_logger.debug("Adding new post: getting tags from db")
            # получаем уже существующие теги из базы
            res = await self.db_session.execute(select(TagModel).where(TagModel.name.in_(new_post.tags)))
            existing_tags = res.scalars().all()
            existing_tags_dict = {tag.name: tag for tag in existing_tags}
            
            default_logger.debug("Adding new post: add tags to post")
            # если тега в базе нету создаем новую модель и добавляем к посту
            # если есть, то сразу добавляем к посту
            # обратную связь Tag-Post алхимия сама создаст 
            for tag_name in new_post.tags:
                if tag_name in existing_tags_dict:
                    post_model.tags.append(existing_tags_dict[tag_name])
                else:
                    new_tag = TagModel(name=tag_name)
                    post_model.tags.append(new_tag)
        
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
        
        await self.db_session.commit()
        # подгружаем теги и файлы
        await self.db_session.refresh(post_model, attribute_names=["tags", "attachments"])
        
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
    
    async def get_post_with_comments_count(self, post_id: UUID, 
                             load_options: Sequence[ORMOption] | None = None) -> tuple[PostModel, int]:
        
        default_logger.debug("Getting post with comments count")

        subq_comments_count = (select(func.count(CommentModel.id))
                            .where(CommentModel.post_id == PostModel.id)
                            .scalar_subquery())
        query = (select(PostModel, subq_comments_count.label("comments_count"))
                    .where(PostModel.id==post_id))
        
        if load_options:
            query = query.options(*load_options)
        
        res = await self.db_session.execute(query)
        
        post = res.first()
            
        if post is None:
            default_logger.debug("Getting post with comments count: Error. Post not found")
            raise PostNotFoundException("Post not found in db")
        
        return cast(tuple[PostModel, int], post)
        
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
        
        
    
    # return: (total_count_posts, list[post, comments_count])
    async def get_posts(self, 
            limit: int, offset: int,
            sort: PostsSortEnum, period: PeriodEnum,
            load_options: Sequence[ORMOption] | None = None) -> tuple[int, Sequence[tuple[PostModel, int]]]:
        
        default_logger.debug(f"Getting posts from db: limit={limit}, offset={offset}")
        
        subq_comments_count = (
            select(func.count(CommentModel.id))
            .where(CommentModel.post_id == PostModel.id)
            .scalar_subquery()
        )

        query = (
            select(
                PostModel,
                subq_comments_count.label("comments_count")
            )
            .options(defer(PostModel.body))
        )

        match sort:

            case PostsSortEnum.NEW:
                query = query.order_by(PostModel.created_at.desc())

            case PostsSortEnum.POPULAR:

                match period:

                    case PeriodEnum.ALL_TIME:
                        pass

                    case PeriodEnum.DAY:
                        border = datetime.now() - timedelta(days=1)
                        query = query.where(PostModel.created_at >= border)

                    case PeriodEnum.WEEK:
                        border = datetime.now() - timedelta(weeks=1)
                        query = query.where(PostModel.created_at >= border)

                    case PeriodEnum.MONTH:
                        border = datetime.now() - timedelta(days=30)
                        query = query.where(PostModel.created_at >= border)

                    case PeriodEnum.YEAR:
                        border = datetime.now() - timedelta(days=365)
                        query = query.where(PostModel.created_at >= border)

                query = query.order_by(PostModel.views_count.desc())

        count_query = (
            select(func.count())
            .select_from(query.order_by(None).subquery())
        )

        result = await self.db_session.execute(count_query)
        total_count = result.scalar_one()

        query = (
            query
            .limit(limit)
            .offset(offset)
        )

        if load_options:
            query = query.options(*load_options)

        result = await self.db_session.execute(query)
        posts = result.all()
        
        return cast(tuple[int, list[tuple[PostModel, int]]], (total_count, posts))
    
    async def update_post(self, post_id: UUID, author_id: UUID, post_data: PostPatchDTO) -> PostModel:
        default_logger.debug("Updating post: start")
        
        # словарь с только указанными полями в запросе
        only_updated_data = post_data.model_dump(exclude_unset=True)
        
        if not only_updated_data:
            default_logger.debug("Updating post: nothing to update")
            # все поля пустые
            # ничего не меняем
            # возвращаем этот пост
            options = [selectinload(PostModel.tags), selectinload(PostModel.attachments)]
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

                # получаем уже существующие теги из базы
                res = await self.db_session.execute(select(TagModel).where(TagModel.name.in_(updated_tags)))
                existing_tags = res.scalars().all()
                existing_tags_dict = {tag.name: tag for tag in existing_tags}
                
                # удаляем все старые теги с поста
                post_model.tags = []
                
                # Если пользователь передал новые теги которых нету в базе,
                # то создаем новую модель. алхимия потом сама добавит новый тег в базу
                for tag_name in updated_tags:
                    if tag_name in existing_tags_dict:
                        post_model.tags.append(existing_tags_dict[tag_name])
                    else:
                        new_tag = TagModel(name=tag_name)
                        post_model.tags.append(new_tag)
                
                default_logger.error("Updating post: all tags updated")
                # алхимия сама добавит новые теги в базу
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
        await self.db_session.commit()
        await self.db_session.refresh(post_model, attribute_names=["tags", "attachments"])
        
        # удаляем файлы с хранилища если такие есть
        if filenames_to_delete:
            default_logger.debug("Updating post: delete files from storage")
            for filename in filenames_to_delete:
                if self.storage:
                    self.storage.delete(filename)
                else:
                    default_logger.error("Updating post: cant delete files. storage isn't set")
        
        return post_model

    async def add_reaction_to_post(self, reaction_data: PostAddReactionDTO, user_id: UUID):
        default_logger.debug("Adding reaction to post: check if post exists")
        post = await self.get_post_by_id(reaction_data.post_id)
        # если поста нету, будет raise error
        
        default_logger.debug("Adding reaction to post: check if user already reacted to this post")
        query = (select(PostReactionModel)
                .where(and_(PostReactionModel.user_id==user_id,
                            PostReactionModel.post_id==reaction_data.post_id)))
        res = await self.db_session.execute(query)
        reaction = res.scalar_one_or_none()
        
        if reaction and reaction.reaction_type == reaction_data.reaction_type:
            default_logger.debug("Adding reaction to post: user made same reaction. do not nothing")
            return None
        elif reaction and reaction.reaction_type != reaction_data.reaction_type:
            default_logger.debug("Adding reaction to post: user changed reaction to post")
            reaction.reaction_type = reaction_data.reaction_type
        else:
            default_logger.debug("Adding reaction to post: user adding new reaction to post")
            reaction_model = PostReactionModel(user_id=user_id,
                                               post_id=reaction_data.post_id,
                                               reaction_type=reaction_data.reaction_type)
            self.db_session.add(reaction_model)
        
        await self.db_session.commit()
        default_logger.info("Adding reaction to post: reaction added")
        
    async def get_all_existing_tags(self,
                                    limit: int, offset: int,
                                    load_options: Sequence[ORMOption] | None = None) -> Sequence[TagModel]:
        query = select(TagModel).limit(limit).offset(offset)
        if load_options:
            query = query.options(*load_options)
        res = await self.db_session.execute(query)
        return res.scalars().all()
        
    async def get_all_post_tags(self, post_id: UUID) -> list[TagModel]:
        query = (select(PostModel)
                 .where(PostModel.id==post_id)
                 .options(selectinload(PostModel.tags)))
        res = await self.db_session.execute(query)
        post = res.scalar_one_or_none()
        if post is None:
            raise PostNotFoundException("Post not found")
        
        return post.tags
    
    async def get_all_post_reactions(self, post_id: UUID) -> dict[TypeReactionEnum, int]:
        query = (select(PostModel)
                 .where(PostModel.id==post_id)
                 .options(selectinload(PostModel.reactions_list)))
        res = await self.db_session.execute(query)
        post = res.scalar_one_or_none()
        if post is None:
            raise PostNotFoundException("Post not found")
        
        return post.reactions
    
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
    
    # find posts by title using trigramms
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