from typing import Sequence, cast
from uuid import UUID
from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy.orm.interfaces import ORMOption

from source.models.comment import CommentModel
from source.models.user import UserModel
from source.models.comment_reaction import CommentReactionModel
from source.models.attachment_media import AttachmentMediaModel
from source.schemas.comment import (CommentAddDTO, 
                                    CommentPatchDTO, 
                                    CommentAddReactionDTO)
from source.core.exceptions import (CommentNotFoundException, 
                                    PostNotFoundException, 
                                    FileNotFoundException)
from source.core.logger import default_logger
from source.core.types import TypeReactionEnum
from source.services.storage.baseStorage import BaseStorage


class CommentRepository:
    
    def __init__(self, db_session: AsyncSession, storage: BaseStorage):
        self.db_session = db_session
        self.storage = storage
        
    async def add_comment(self, 
                          new_comment: CommentAddDTO, 
                          author_id: UUID,
                          post_id: UUID) -> CommentModel:

        comment_data = new_comment.model_dump(exclude={"files_id"})
        comment_model = CommentModel(**comment_data)
        comment_model.author_id = author_id
        comment_model.post_id = post_id
                 
        self.db_session.add(comment_model)
        
        # attachment files
        if new_comment.files_id:
            default_logger.debug("Adding new comment: loading media files")
            await self.db_session.flush()
            query = (select(AttachmentMediaModel)
                     .where(and_(AttachmentMediaModel.id.in_(new_comment.files_id),
                                 AttachmentMediaModel.user_id == author_id,
                                 AttachmentMediaModel.is_temporary.is_(True),
                                 AttachmentMediaModel.post_id.is_(None),
                                 AttachmentMediaModel.comment_id.is_(None))))
            attachment_res = await self.db_session.execute(query)
            attachments = attachment_res.scalars().all()
            
            if not attachments:
                default_logger.error("Adding new comment: Error. Uploaded media files not found in db")
                raise FileNotFoundException("media files not found in db")
            if len(attachments) != len(new_comment.files_id):
                default_logger.error("Adding new comment: Error. files in db and files in request dont match")
                raise FileNotFoundException("Amount of files dont match")
            
            for attachment in attachments:
                attachment.comment_id = comment_model.id
                attachment.is_temporary = False
            
            default_logger.debug("Adding new comment: files added")
        
        await self.db_session.commit()

        await self.db_session.refresh(comment_model, attribute_names=["attachments", "author"])
        
        return comment_model
    
    async def delete_comment(self, comment_id: UUID, user_id: UUID) -> tuple[UUID, UUID]:
        # returning: comment_id, post_id
        
        query = (delete(CommentModel)
                 .where(and_(CommentModel.id==comment_id,
                             CommentModel.author_id==user_id))
                 .returning(CommentModel.id, CommentModel.post_id))
        result_db = await self.db_session.execute(query)
        result = result_db.first()
        if result is None:
            default_logger.error(f"Deleting comment. Error. Comment not found or user are not author")
            raise CommentNotFoundException("Comment not found or you are not author")
        await self.db_session.commit()
        
        return cast(tuple[UUID, UUID], result)
    
    async def get_comments_by_ids(self, 
                comment_ids: list[UUID], 
                user_id: UUID | None, 
                load_options: Sequence[ORMOption] | None = None) -> Sequence[tuple[CommentModel,
                                                                             str,
                                                                             int,
                                                                             TypeReactionEnum | None]]:
        # returing: [(CommentModel, author_username, count_replies, user_reaction)]
        
        # нужен псевдоним чтобы правильно создался sql запрос
        Reply = aliased(CommentModel)
        subq_replies_count = (
            select(func.count(Reply.id))
            .where(Reply.parent_id == CommentModel.id)
            .correlate(CommentModel)
            .scalar_subquery()
        )
        query = (
            select(CommentModel, 
                   UserModel.username.label("author_username"),
                   subq_replies_count.label("count_replies"),
                   CommentReactionModel.reaction_type.label("user_reaction"))
            # никнейм автора комментария
            .join(UserModel, CommentModel.author_id == UserModel.id)
            # реакция текущего пользователя на комментарий
            .outerjoin(CommentReactionModel, and_(CommentReactionModel.comment_id == CommentModel.id,
                                                  CommentReactionModel.user_id == user_id))
            .where(CommentModel.id.in_(comment_ids))
            .order_by(CommentModel.created_at.desc())
        )
        
        if load_options:
            query = query.options(*load_options)
        
        res = await self.db_session.execute(query)
        
        comments = res.all()
        
        if comments is None:
            raise PostNotFoundException("Post not found or post doesnt have comments")
        
        return cast(list[tuple[CommentModel, str, int, TypeReactionEnum | None]], comments)
    
    async def get_comment_by_id(self, comment_id: UUID, 
                                load_options: Sequence[ORMOption] | None = None) -> CommentModel:
        
        default_logger.debug("Getting comment from db by id")

        query = select(CommentModel).where(CommentModel.id==comment_id)
        if load_options:
            query = query.options(*load_options)
        
        res = await self.db_session.execute(query)
        comment =  res.scalar_one_or_none()
        if comment is None:
            default_logger.debug("Getting comment from db: Error. Comment not found")
            raise CommentNotFoundException("Comment not found in db")
        return comment
        
    # получить корневые комментарии поста 
    # (то есть те которые НЕ являются ответами на другие комменты)
    # вместе с количеством прямых ответов
    async def get_post_root_comments(self, 
            user_id: UUID | None,
            post_id: UUID, 
            limit: int, offset: int,
            load_options: Sequence[ORMOption] | None = None) -> Sequence[tuple[CommentModel, 
                                                                               str, 
                                                                               int,
                                                                               TypeReactionEnum | None]]:
        # return: [(<CommentModel>, <author_username>, <count_replies>, <user_reaction>)]
        
        default_logger.debug(f"Getting root comments for post from db: limit={limit}, offset={offset}")
        
        # нужен псевдоним чтобы правильно создался sql запрос
        Reply = aliased(CommentModel)
        subq_replies_count = (
            select(func.count(Reply.id))
            .where(Reply.parent_id == CommentModel.id)
            .correlate(CommentModel)
            .scalar_subquery()
        )
        query = (
            select(CommentModel, 
                   UserModel.username.label("author_username"),
                   subq_replies_count.label("count_replies"),
                   CommentReactionModel.reaction_type.label("user_reaction"))
            # никнейм автора комментария
            .join(UserModel, CommentModel.author_id == UserModel.id)
            # реакция текущего пользователя на комментарий
            .outerjoin(CommentReactionModel, and_(CommentReactionModel.comment_id == CommentModel.id,
                                                  CommentReactionModel.user_id == user_id))
            .where(
                and_(
                    CommentModel.post_id == post_id,
                    CommentModel.parent_id == None,
                )
            )
            .order_by(CommentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        if load_options:
            query = query.options(*load_options)
        
        res = await self.db_session.execute(query)
        
        comments = res.all()
        
        if comments is None:
            raise PostNotFoundException("Post not found or post doesnt have comments")
        
        return cast(list[tuple[CommentModel, str, int, TypeReactionEnum | None]], comments)
    
    # корневые ответы на комментарий 
    # (ответы на другие комменты под этим комментом не учитываются)
    async def get_comment_root_replies(self, 
            user_id: UUID | None,
            comment_id: UUID, 
            limit: int, offset: int,
            load_options: Sequence[ORMOption] | None = None) -> Sequence[tuple[CommentModel, 
                                                                               str, 
                                                                               int,
                                                                               TypeReactionEnum | None]]:
        
        default_logger.debug(f"Getting replies on comment from db: limit={limit}, offset={offset}")
        
        Reply = aliased(CommentModel)
        subq_replies_count = (
            select(func.count(Reply.id))
            .where(Reply.parent_id == CommentModel.id)
            .correlate(CommentModel)
            .scalar_subquery()
        )
        query = (
            select(CommentModel,
                   UserModel.username.label("author_username"),
                   subq_replies_count.label("count_replies"),
                   CommentReactionModel.reaction_type.label("user_reaction"))
            # никнейм автора комментария
            .join(UserModel, CommentModel.author_id == UserModel.id)
            # реакция текущего пользователя на комментарий
            .outerjoin(CommentReactionModel, and_(CommentReactionModel.comment_id == CommentModel.id,
                                                  CommentReactionModel.user_id == user_id))
            .where(CommentModel.parent_id == comment_id)
            .order_by(CommentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        if load_options:
            query = query.options(*load_options)
        
        res = await self.db_session.execute(query)
        
        comments = res.all()
        
        if comments is None:
            default_logger.debug("Getting replies on comment: Error. Comment doesnt have any replies or comment not found")
            raise CommentNotFoundException("Comment doesnt have any replies or comment not found")
        
        return cast(list[tuple[CommentModel, str, int, TypeReactionEnum | None]], comments)
    
    async def update_comment(self, comment_id: UUID, author_id: UUID, 
                             comment_data: CommentPatchDTO) -> CommentModel:
        
        default_logger.debug("Updating comment: start")
        
        # словарь только с указанными полями в запросе
        only_updated_data = comment_data.model_dump(exclude_unset=True)
        
        if not only_updated_data:
            default_logger.debug("Updating comment: nothing to update")
            # все поля пустые
            # ничего не меняем
            options = [selectinload(CommentModel.attachments)]
            return await self.get_comment_by_id(comment_id, options)
        
        # Файлы обновим отдельно
        updated_files_id = only_updated_data.pop("files_id", None)
        
        # достаем коммент
        default_logger.debug("Updating comment: getting post from db")
        query = (select(CommentModel)
                 .where(and_(CommentModel.id==comment_id, CommentModel.author_id==author_id))
                 .options(selectinload(CommentModel.attachments)))
        result = await self.db_session.execute(query)
        comment_model = result.scalar_one_or_none()
        if comment_model is None:
            default_logger.error(f"Updating comment. Error. Comment not found or user is not author")
            raise CommentNotFoundException("Comment not found or you dont have permissions to update this post")
            
        # обновляем переданные поля
        default_logger.debug("Updating comment: updating comment columns")
        for key, value in only_updated_data.items():
            setattr(comment_model, key, value)
        
        # обновляем файлы
        filenames_to_delete = []
        if updated_files_id is not None:
            default_logger.debug("Updating comment: updating attachments")
            
            # Конвертируем пришедшие ID в UUID для корректного сравнения
            target_ids = {UUID(f_id) if isinstance(f_id, str) else f_id for f_id in updated_files_id}
            current_attachments = {att.id: att for att in comment_model.attachments}
            current_ids = set(current_attachments.keys())
            
            # Определяем, какие файлы нужно удалить (они есть в модели, но их нет в запросе)
            ids_to_remove = current_ids - target_ids
            # Определяем, какие файлы нужно добавить (они есть в запросе, но их нет в модели)
            ids_to_add = target_ids - current_ids
            
            # Удаляем старые файлы
            if ids_to_remove:
                default_logger.debug(f"Updating comment: removing {len(ids_to_remove)} files")
                for file_id in ids_to_remove:
                    file_to_delete = current_attachments[file_id]
                    # Если у тебя настроен каскад delete-orphan, удаление из списка удалит запись из БД
                    comment_model.attachments.remove(file_to_delete)
                    
                    filenames_to_delete.append(file_to_delete.filename)
            
            # Добавляем новые файлы
            if ids_to_add:
                default_logger.debug(f"Updating comment: loading {len(ids_to_add)} new media files")
                
                query_files = (
                    select(AttachmentMediaModel)
                    .where(and_(
                        AttachmentMediaModel.id.in_(ids_to_add),
                        AttachmentMediaModel.user_id == author_id,
                        AttachmentMediaModel.is_temporary.is_(True),
                        AttachmentMediaModel.comment_id.is_(None)
                    ))
                )
                attachments_res = await self.db_session.execute(query_files)
                new_attachments = attachments_res.scalars().all()
                
                if len(new_attachments) != len(ids_to_add):
                    default_logger.error("Updating comment: Error. New media files not found or access denied")
                    raise FileNotFoundException("Some uploaded media files were not found or invalid")
                
                for attachment in new_attachments:
                    attachment.is_temporary = False
                    attachment.comment_id = comment_id
                    comment_model.attachments.append(attachment)
        
        default_logger.debug("Updating comment: saving")
        # сохраняем
        await self.db_session.commit()
        await self.db_session.refresh(comment_model)
        
        # удаляем файлы с хранилища если такие есть
        if filenames_to_delete:
            default_logger.debug("Updating comment: delete files from storage")
            for filename in filenames_to_delete:
                self.storage.delete(filename)
        
        return comment_model

    async def add_reaction_to_comment(self, 
                    reaction_data: CommentAddReactionDTO, 
                    user_id: UUID) -> tuple[TypeReactionEnum | None, TypeReactionEnum | None]:
        # return: (old reaction, new reaction)
        
        default_logger.debug("Adding reaction to comment: check if comment exists")
        comment = await self.get_comment_by_id(reaction_data.comment_id)
        # если коммента нету, будет raise error CommentNofFound
        
        default_logger.debug("Adding reaction to comment: check if user already reacted to this comment")
        query = (select(CommentReactionModel)
                .where(and_(CommentReactionModel.user_id==user_id,
                            CommentReactionModel.comment_id==reaction_data.comment_id)))
        res = await self.db_session.execute(query)
        reaction = res.scalar_one_or_none()
        
        old_reaction: TypeReactionEnum | None = None
        new_reaction: TypeReactionEnum | None = None
        
        if reaction and reaction.reaction_type == reaction_data.reaction_type:
            default_logger.debug("Adding reaction to comment: user made same reaction. delete his reaction")
            
            old_reaction = reaction.reaction_type
            
            await self.db_session.delete(reaction)
            
        elif reaction and reaction.reaction_type != reaction_data.reaction_type:
            default_logger.debug("Adding reaction to comment: user changed his reaction")
            
            old_reaction = reaction.reaction_type
            new_reaction = reaction_data.reaction_type 
            
            reaction.reaction_type = reaction_data.reaction_type
            
        else:
            default_logger.debug("Adding reaction to comment: user adding new reaction to comment")
            reaction_model = CommentReactionModel(user_id=user_id,
                                                  comment_id=reaction_data.comment_id,
                                                  reaction_type=reaction_data.reaction_type)
            self.db_session.add(reaction_model)
            
            new_reaction = reaction_data.reaction_type
        
        default_logger.debug("Adding reaction to comment: reaction added")
        await self.db_session.commit()
    
        return (old_reaction, new_reaction)

    async def get_all_comment_reactions(self, 
                                        comment_id: UUID) -> dict[TypeReactionEnum, int]:

        query = (select(CommentModel)
                 .where(CommentModel.id==comment_id)
                 .options(selectinload(CommentModel.reactions_list)))
        res = await self.db_session.execute(query)
        comment = res.scalar_one_or_none()
        if comment is None:
            default_logger.error("Getting all comment' reactions: Comment not found in db")
            raise CommentNotFoundException("Comment not found")
        
        return comment.reactions
        
    