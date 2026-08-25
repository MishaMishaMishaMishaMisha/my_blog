from sqladmin import ModelView
from fastapi.requests import Request

from source.models.user import UserModel
from source.core.security import hash_password
from source.core.utils import get_random_string

class UserAdmin(ModelView, model=UserModel):

    # колонки которые будут отображаться в списке пользователей
    column_list = [UserModel.id,
                   UserModel.username,
                   UserModel.email,
                   UserModel.role,
                   UserModel.is_active,
                   UserModel.is_verified,
                   UserModel.created_at,
                   UserModel.updated_at,
                   UserModel.last_seen,
                   UserModel.last_login]
    
    # сделаем сортировку. True значит descending
    column_default_sort = [(UserModel.created_at, True)]
    
    # изменяем название колонки с паролем
    column_labels = {UserModel.password_hash: "password"}
    
    # запрет на редактирование полей
    form_excluded_columns = [UserModel.id,
                             UserModel.posts,
                             UserModel.comments,
                             UserModel.user_reactions_on_posts,
                             UserModel.user_reactions_on_comments,
                             UserModel.created_at,
                             UserModel.updated_at,
                             UserModel.last_seen,
                             UserModel.last_login]
    
    # хеширование пароля при создании/редактировании
    # этот сам метод вызывается как при создании так и при редактировании 
    async def on_model_change(self, 
                              data: dict, 
                              model: UserModel, 
                              is_created: bool, 
                              request: Request) -> None:
        
        # данные приходят незахешированные хоть и называются так
        raw_password = data.get("password_hash") or get_random_string()
        if is_created or model.password_hash != raw_password:
            data.update(password_hash=hash_password(raw_password))
        