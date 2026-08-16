from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime

from source.core.types import RoleEnum


class UserAddDTO(BaseModel):
    username: str = Field(min_length=5, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=50)
    
class UserLoginDTO(BaseModel):
    login: str = Field(..., description="username or email")
    password: str
    
# обновление обычных данных пользователя
class UserPatchDTO(BaseModel):
    username: str | None = Field(default=None, min_length=5, max_length=20)
    # другие поля в будущем
    
# обновление пароля
class UserPatchPassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=50)
    new_password: str = Field(min_length=8, max_length=50)

# обновление почты
class UserPatchEmail(BaseModel):
    new_email: EmailStr
    confirm_password: str = Field(min_length=8, max_length=50)
    
# сброс пароля
class UserResetPasswordDTO(BaseModel):
    token: str
    new_password: str
    
class UserEmailDTO(BaseModel):
    user_email: EmailStr


# response
class UserDTO(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    role: RoleEnum
    is_active: bool
    is_verified: bool
    last_login: datetime
    last_seen: datetime
    
    model_config = {'from_attributes': True}
    
class UserPublicProfileDTO(BaseModel):
    username: str
    is_verified: bool
    created_at: datetime
    last_seen: datetime
    posts_count: int = 0
    comments_count: int = 0
    
    role: RoleEnum
    
    model_config = {'from_attributes': True}  
