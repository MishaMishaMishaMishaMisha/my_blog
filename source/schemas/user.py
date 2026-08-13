from pydantic import BaseModel, Field, EmailStr
from source.core.types import RoleEnum
from uuid import UUID
from datetime import datetime


# adding new user
class UserAddDTO(BaseModel):
    username: str = Field(min_length=5, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=50)
    
# authenticating user
class UserLoginDTO(BaseModel):
    login: str = Field(..., description="username or email")
    password: str
    
# updating user's fields except password and email
class UserPatchDTO(BaseModel):
    username: str | None = Field(default=None, min_length=5, max_length=20)
    # other fields...
    
# update user's password
class UserPatchPassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=50)
    new_password: str = Field(min_length=8, max_length=50)

# update user's email
class UserPatchEmail(BaseModel):
    new_email: EmailStr
    confirm_password: str = Field(min_length=8, max_length=50)
    
class UserEmailDTO(BaseModel):
    user_email: EmailStr
    
class UserResetPasswordDTO(BaseModel):
    token: str
    new_password: str


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
    
    model_config = {'from_attributes': True}  
