from sqladmin import ModelView

from source.models.tag import TagModel

class TagAdmin(ModelView, model=TagModel):

    # колонки которые будут отображаться в списке тегов
    column_list = [TagModel.id,
                   TagModel.name,
                   TagModel.created_at,
                   TagModel.updated_at]
    
    # сделаем сортировку. True значит descending
    column_default_sort = [(TagModel.created_at, True)]

    # запрет на редактирование полей
    form_excluded_columns = [TagModel.id,
                             TagModel.posts_with_tag,
                             TagModel.created_at,
                             TagModel.updated_at]