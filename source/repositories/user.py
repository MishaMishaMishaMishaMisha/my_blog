from sqlalchemy.ext.asyncio import AsyncSession
from source.models.user import UserModel
from source.schemas.user import UserAddDTO, UserPatchDTO
from sqlalchemy import select, delete
from sqlalchemy.orm.interfaces import ORMOption
from sqlalchemy.exc import IntegrityError
from source.core.exceptions import (UsernameAlreadyExsistsException, 
                                    EmailAlreadyExsistsException, 
                                    UserNotFoundException,
                                    UserInactiveException,
                                    UserAlreadyVerifiedException)
from source.core.logger import default_logger
from typing import Sequence
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

        # обрабтка случая когда одновременно несколько пользователей 
        # отправили данные с одинаковым именем
        try:
            default_logger.debug("Adding new user: TRYING TO ADD USER IN DB")
            self.db_session.add(new_user_model)
            await self.db_session.commit()
        except IntegrityError:
            default_logger.error("Adding new user: ERROR. Username already taken")
            await self.db_session.rollback()
            raise UsernameAlreadyExsistsException("such username already taken")
        
        
        return new_user_model
    
    async def get_user_by(self, 
                          id: UUID | None = None,
                          username: str | None = None,
                          email: str | None = None) -> UserModel | None:
        
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
        
        res = await self.db_session.execute(query)
        return res.scalar_one_or_none()
    
    async def verify_user(self, user_id: UUID) -> None:
        user = await self.get_user_by(id=user_id)
        if not user:
            raise UserNotFoundException("User not found in db")
        if not user.is_active:
            raise UserInactiveException()
        if user.is_verified:
            raise UserAlreadyVerifiedException()
        
        user.is_verified = True
        await self.db_session.commit()
        
    async def reset_password(self, user_id: UUID, password_hash: str) -> None:
        user = await self.get_user_by(id=user_id)
        if not user:
            raise UserNotFoundException("User not found in db")
        if not user.is_active:
            raise UserInactiveException()

        user.password_hash = password_hash
        await self.db_session.commit()
    
    async def delete_user(self, user_id: UUID) -> None:
        query = delete(UserModel).where(UserModel.id==user_id).returning(UserModel.id)
        result = await self.db_session.execute(query)
        deleted_id = result.scalar_one_or_none()
        if deleted_id is None:
            raise UserNotFoundException("User not found in db")
        await self.db_session.commit()
    
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
        