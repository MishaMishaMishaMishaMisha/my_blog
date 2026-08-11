from sqlalchemy.ext.asyncio import AsyncSession
from source.models.user import UserModel
from source.models.post import PostModel
from source.models.comment import CommentModel
from source.schemas.user import UserAddDTO, UserPatchDTO
from sqlalchemy import select, delete, func
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.interfaces import ORMOption
from sqlalchemy.exc import IntegrityError
from source.core.exceptions import (UserException,
                                    UsernameAlreadyExsistsException, 
                                    EmailAlreadyExsistsException, 
                                    UserNotFoundException,
                                    UserInactiveException,
                                    UserAlreadyVerifiedException)
from source.core.logger import default_logger
from typing import Sequence, cast
from uuid import UUID


class UserRepository:
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        
    async def make_commit(self):
        await self.db_session.commit()
        
    async def add_user(self, new_user: UserAddDTO, hashed_password: str) -> UserModel:
        default_logger.debug("Adding new user: CREATING USER MODEL")
        
        user_data = new_user.model_dump(exclude={"password"})
        
        new_user_model = UserModel(**user_data, password_hash=hashed_password)

        try:
            self.db_session.add(new_user_model)
            await self.db_session.commit()
            await self.db_session.refresh(new_user_model)
            return new_user_model

        except IntegrityError as e:
            await self.db_session.rollback()
            # могут быть различные ошибки - никнейм существует, почта существует и др.

            msg = str(e.orig)

            if 'ix_users_username' in msg:
                raise UsernameAlreadyExsistsException("such username already taken")

            if 'ix_users_email' in msg:
                raise EmailAlreadyExsistsException("such email already taken")

            raise UserException(str(e))
    
    async def get_user_profile(self, username: str) -> tuple[UserModel, int, int]:
        
        # 1. Подзапрос для подсчета постов пользователя
        posts_subq = (
            select(func.count(PostModel.id))
            .where(PostModel.author_id == UserModel.id)
            .scalar_subquery()
        )
        
        # 2. Подзапрос для подсчета комментариев пользователя
        comments_subq = (
            select(func.count(CommentModel.id))
            .where(CommentModel.author_id == UserModel.id)
            .scalar_subquery()
        )
        
        # 3. Основной запрос
        stmt = (
            select(
                UserModel,
                posts_subq.label("posts_count"),
                comments_subq.label("comments_count")
            )
            .where(UserModel.username == username)
        )
        
        result = await self.db_session.execute(stmt)
        row = result.first()
        
        if row is None:
            raise UserNotFoundException("User not found in db")
            
        return cast(tuple[UserModel, int, int], row)
    
    async def get_user_by(self, 
                          id: UUID | None = None,
                          username: str | None = None,
                          email: str | None = None,
                          load_options: Sequence[ORMOption] | None = None) -> UserModel | None:
        
        if all(param is None for param in (id, username, email)):
            default_logger.debug("Getting user from db: No id/username/email given")
            raise ValueError("give at least one parameter")
        
        if id is not None:
            default_logger.debug(f"Getting user from db by id = {id}")
            query = select(UserModel).where(UserModel.id==id)
        elif username is not None:
            default_logger.debug(f"Getting user from db by username = {username}")
            query = select(UserModel).where(UserModel.username==username)
        else:
            default_logger.debug(f"Getting user from db by email = {email}")
            query = select(UserModel).where(UserModel.email==email)
            
        if load_options:
            query = query.options(*load_options)
        
        res = await self.db_session.execute(query)
        return res.scalar_one_or_none()
    
    async def verify_user(self, user_id: UUID) -> UserModel:
        user = await self.get_user_by(id=user_id)
        if not user:
            raise UserNotFoundException("User not found in db")
        if not user.is_active:
            raise UserInactiveException()
        if user.is_verified:
            raise UserAlreadyVerifiedException()
        
        user.is_verified = True
        await self.db_session.commit()
        
        return user
        
    async def reset_password(self, user_id: UUID, password_hash: str) -> None:
        user = await self.get_user_by(id=user_id)
        if not user:
            raise UserNotFoundException("User not found in db")
        if not user.is_active:
            raise UserInactiveException()

        user.password_hash = password_hash
        await self.db_session.commit()
    
    async def delete_user(self, user_id: UUID) -> str:
        query = delete(UserModel).where(UserModel.id==user_id).returning(UserModel.username)
        result = await self.db_session.execute(query)
        deleted_username = result.scalar_one_or_none()
        if deleted_username is None:
            raise UserNotFoundException("User not found in db")
        await self.db_session.commit()
        
        return deleted_username
    
    async def get_user(self, user_id: UUID,
                       load_options: Sequence[ORMOption] | None = None) -> UserModel:

        query = select(UserModel).where(UserModel.id==user_id)
        if load_options:
            query = query.options(*load_options)
            
        res = await self.db_session.execute(query)
        user = res.scalar_one_or_none()

        if user is None:
            raise UserNotFoundException("User not found in db")
        
        return user
    
    async def get_users(self, limit: int, offset: int,
                        load_options: Sequence[ORMOption] | None = None) -> Sequence[UserModel]:
        
        query = select(UserModel).order_by(UserModel.created_at.desc()).limit(limit).offset(offset)
        # подгрузка связей если указана
        if load_options:
            query = query.options(*load_options)
        res = await self.db_session.execute(query)
        return res.scalars().all()
    
    async def update_user(self, user_id: UUID, user_data: UserPatchDTO) -> UserModel:
     
        # словарь только с указанными полями в запросе
        only_updated_data = user_data.model_dump(exclude_unset=True)
        
        if not only_updated_data:
            default_logger.debug("Updating user: nothing to update")
            # все поля пустые
            # ничего не меняем
            return await self.get_user(user_id)
        
        # достаем пользователя
        default_logger.debug("Updating user: getting user from db")
        user_model = await self.get_user(user_id)
        # если user не найден, будет ошибка которая обрабатывается в другом месте
            
        # обновляем переданные поля
        default_logger.debug("Updating user: updating user columns")
        for key, value in only_updated_data.items():
            
            if key=="username":
                existing_username = await self.get_user_by(username=value)
                if existing_username:
                    default_logger.error("Updating user: ERROR. USERNAME ALREADY IN DB")
                    raise UsernameAlreadyExsistsException("such username already in db")
            
            if key=="email":
                existing_email = await self.get_user_by(email=value)
                if existing_email:
                    default_logger.error("Updating user: ERROR. EMAIL ALREADY IN DB")
                    raise EmailAlreadyExsistsException("such email already in db")
                
                user_model.is_verified = False
            
            setattr(user_model, key, value)
        
        
        default_logger.debug("Updating user: saving")
        # сохраняем
        await self.db_session.commit()
        await self.db_session.refresh(user_model)
        return user_model
        
    
    # принимает часть имени либо полное имя
    # ищет все совпадения и возвращает их
    async def find_user_by_name(self, seacrhing_name: str,
                                load_options: Sequence[ORMOption] | None = None) -> Sequence[UserModel]:
        
        query = select(UserModel).where(UserModel.username.ilike(f"%{seacrhing_name}%"))
        if load_options:
            query = query.options(*load_options)
        res = await self.db_session.execute(query)
        return res.scalars().all()
        
        
        
        
        
        
