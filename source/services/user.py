from source.repositories.user import UserRepository
from source.models.user import UserModel
from source.models.post import PostModel
from source.models.comment import CommentModel
from source.schemas.user import (UserAddDTO, 
                                 UserPatchDTO, 
                                 UserPatchPassword,
                                 UserPatchEmail,
                                 UserPublicProfileDTO)
from source.schemas.post import PostPreviewDTO, PostListDTO
from source.core.exceptions import (UsernameAlreadyExsistsException, 
                                    EmailAlreadyExsistsException,
                                    UserNotFoundException,
                                    InvalidCredentialsException,
                                    UserException)
from sqlalchemy.exc import IntegrityError
from source.core.logger import default_logger
from source.core.security import hash_password, verify_password
from uuid import UUID
from typing import Sequence, Set
from enum import Enum
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import ORMOption
from datetime import datetime, timedelta, timezone
from source.schemas.user import UserDTO
from source.cache.redis_backend import RedisBackend


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
    
    def __init__(self, user_repo: UserRepository, cache_redis: RedisBackend):
        self.user_repo = user_repo
        self.cache_redis = cache_redis
        
        self.cache_user_key = "user-profile:{username}"
        self.cache_user_ttl = 300 # 5 minutes
        
    async def create_new_user(self, new_user: UserAddDTO) -> UserDTO:
        default_logger.debug("Adding new user: CHECKING IF USERNAME IN DB")
        
        hashed_password = hash_password(new_user.password)

        db_user = await self.user_repo.add_user(new_user, hashed_password)

        return UserDTO.model_validate(db_user)
    
    async def delete_user(self, user_id: UUID) -> None:
        username = await self.user_repo.delete_user(user_id)
        
        default_logger.debug("deleting user from cache")
        await self.cache_redis.delete(key=self.cache_user_key.format(username=username))
        
    async def get_user_profile(self, username: str) -> UserPublicProfileDTO:
        
        default_logger.debug("Getting user profile: checking cache")
        # проверяем кеш
        user_cached = await self.cache_redis.get(key=self.cache_user_key.format(username=username))
        if user_cached:
            default_logger.debug("Getting user profile: get user from cache")
            return UserPublicProfileDTO.model_validate(user_cached)
        
        default_logger.debug("Getting user profile: try to find user in db")
        user_data = await self.user_repo.get_user_profile(username)
        

        default_logger.debug("Getting user profile: user found. validating...")
        user = (UserPublicProfileDTO
               .model_validate(user_data[0])
               .model_copy(update={"posts_count": user_data[1]})
               .model_copy(update={"comments_count": user_data[2]}))
        
        default_logger.debug("Getting user profile: adding user to cache")
        # добавляем в кеш на 5 минут
        await self.cache_redis.set(key=self.cache_user_key.format(username=username),
                                   value=user.model_dump(mode="json"), 
                                   ttl_seconds=self.cache_user_ttl)
        
        return user
    
    async def get_user(self, user_id: UUID) -> UserModel:
        return await self.user_repo.get_user(user_id)
        
    async def get_users(self, limit: int, offset: int, 
                        include: Set[UserLoadRelations] | None = None) -> Sequence[UserDTO]:
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        db_users = await self.user_repo.get_users(limit, offset, options)

        return [UserDTO.model_validate(db_user) for db_user in db_users]
    
    async def update_user(self, user_id: UUID, user_data: UserPatchDTO) -> UserDTO:
        
        user_db = await self.user_repo.update_user(user_id, user_data)
        
        default_logger.debug("Deleting user from cache")
        await self.cache_redis.delete(key=self.cache_user_key.format(username=user_db.username))
        
        return UserDTO.model_validate(user_db)
    
    async def update_password(self, user_id: UUID, password_data: UserPatchPassword) -> None:
        
        user = await self.user_repo.get_user(user_id)
        
        if not verify_password(password_data.current_password, user.password_hash):
            raise InvalidCredentialsException("Incorrect password")
        
        user.password_hash = hash_password(password_data.new_password)
        
        await self.user_repo.make_commit()
        
    async def update_email(self, user_id: UUID, email_data: UserPatchEmail) -> None:
        
        user = await self.user_repo.get_user(user_id)
        
        if not verify_password(email_data.confirm_password, user.password_hash):
            raise InvalidCredentialsException("Incorrect password")
        
        user.email = email_data.new_email
        
        user.is_verified = False
        
        try:
            await self.user_repo.make_commit()
            
        except IntegrityError as e:
            await self.user_repo.make_rollback()
            
            msg = str(e.orig)

            if 'ix_users_email' in msg:
                raise EmailAlreadyExsistsException("such email already taken")

            raise UserException(str(e))
    
    async def find_user_by_name(self, seacrhing_name: str,
                                include: Set[UserLoadRelations] | None = None) -> Sequence[UserDTO]:
        
        options: Sequence[ORMOption] | None = None
        if include:
            options = self.add_loading_options(include)
        
        db_users = await self.user_repo.find_user_by_name(seacrhing_name, options)
        return [UserDTO.model_validate(db_user) for db_user in db_users]
    
    async def set_last_seen(self, user: UserModel) -> None:
        now = datetime.now(timezone.utc)
        #now = datetime.now()
        # обновляем не чаще чем через 5 минут
        # чтобы не делать commit на каждой операции пользователя
        if (user.last_seen is None or now - user.last_seen > timedelta(minutes=5)):
            user.last_seen = now
            await self.user_repo.make_commit()
    
    
    def add_loading_options(self, include: Set[UserLoadRelations]) -> Sequence[ORMOption]:
        return [self._LOAD_MAP[rel] for rel in include if rel in self._LOAD_MAP]
    
