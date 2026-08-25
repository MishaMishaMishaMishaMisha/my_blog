from sqladmin import ModelView

from source.models.post import PostModel

class PostAdmin(ModelView, model=PostModel):

    # колонки которые будут отображаться в списке тегов
    column_list = [PostModel.id,
                   PostModel.author_id,
                   PostModel.title,
                   PostModel.views_count,
                   PostModel.created_at,
                   PostModel.updated_at]
    
    form_include_pk = True
    
    # сделаем сортировку. True значит descending
    column_default_sort = [(PostModel.created_at, True)]

    # запрет на редактирование полей
    form_excluded_columns = [PostModel.id,
                             PostModel.author_id,
                             PostModel.created_at,
                             PostModel.updated_at,
                             PostModel.attachments,
                             PostModel.author]