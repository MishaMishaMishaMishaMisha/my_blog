from source.repositories.user import UserRepository
from source.models.user import UserModel
from source.schemas.user import UserAddDTO, UserPatchDTO
from source.core.exceptions import UsernameAlreadyExsistsException, EmailAlreadyExsistsException
from source.core.logger import default_logger
from source.core.security import hash_password
from uuid import UUID
from typing import Sequence, Set
from enum import Enum
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import ORMOption
from datetime import datetime, timedelta
from source.schemas.user import UserDTO


class UserLoadRelations(str, Enum):
    POSTS = "posts"
    COMMENTS = "comments"
    REACTIONS_ON_POSTS = "reactions_on_posts"
    REACTIONS_ON_COMMENTS = "reactions_on_comments"
    

class UserService:
    
    _LOAD_MAP = {
        UserLoadRelations.POSTS: selectinload(UserModel.posts),
        UserLoadRelations.COMMENTS: selectinload(UserModel.comments),
        UserLoadRelations.REACTIONS_ON_POSTS: selectinload(UserModel.user_reactions_on_posts),
        UserLoadRelations.REACTIONS_ON_COMMENTS: selectinload(UserModel.user_reactions_on_comments)
    }
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        
    async def create_new_user(self, new_user: UserAddDTO) -> UserDTO:
        default_logger.debug("Adding new user: CHECKING IF USERNAME IN DB")
        
        existing_username = await self.user_repo.get_user_by(username=new_user.username)
        if existing_username:
            default_logger.error("Adding new user: ERROR. USERNAME IN DB")
            raise UsernameAlreadyExsistsException("such username already in db")
        
        existing_email = await self.user_repo.get_user_by(email=new_user.email)
        if existing_email:
            default_logger.error("Adding new user: ERROR. EMAIL IN DB")
            raise EmailAlreadyExsistsException("such email already in db")

        hashed_password = hash_password(new_user.password)
        
        db_user = await self.user_repo.add_user(new_user, hashed_password)
        return UserDTO.model_validate(db_user)
    
    async def delete_user(self, user_id: UUID) -> None:
        await self.user_repo.delete_user(user_id)
        
    async def get_user(self, user_id: UUID,
                       include: Set[UserLoadRelations] | None = None) -> UserDTO:

        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        user_db = await self.user_repo.get_user(user_id, options)
        return UserDTO.model_validate(user_db)
        
    async def get_users(self, limit: int, offset: int, 
                        include: Set[UserLoadRelations] | None = None) -> Sequence[UserDTO]:
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        db_users = await self.user_repo.get_users(limit, offset, options)

        return [UserDTO.model_validate(db_user) for db_user in db_users]
    
    async def update_user(self, user_id: UUID, user_data: UserPatchDTO) -> UserDTO:
        password = user_data.password
        if password is not None:
            default_logger.debug("Updating user: hashing new password")
            hashed_password = hash_password(password)
            user_data.password = hashed_password
        
        user_db = await self.user_repo.update_user(user_id, user_data)
        return UserDTO.model_validate(user_db)
    
    async def find_user_by_name(self, seacrhing_name: str,
                                include: Set[UserLoadRelations] | None = None) -> Sequence[UserDTO]:
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        db_users = await self.user_repo.find_user_by_name(seacrhing_name, options)
        return [UserDTO.model_validate(db_user) for db_user in db_users]
    
    async def set_last_seen(self, user: UserModel) -> None:
        now = datetime.now()
        # обновляем не чаще чем через 5 минут
        # чтобы не делать commit на каждой операции пользователя
        if (user.last_seen is None or now - user.last_seen > timedelta(minutes=5)):
            user.last_seen = now
            await self.user_repo.make_commit()
    
    
    def add_loading_options(self, include: Set[UserLoadRelations]) -> Sequence[ORMOption]:
        return [self._LOAD_MAP[rel] for rel in include if rel in self._LOAD_MAP]
    
