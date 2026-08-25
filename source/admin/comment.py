from sqladmin import ModelView

from source.models.comment import CommentModel

class CommentAdmin(ModelView, model=CommentModel):

    # колонки которые будут отображаться в списке тегов
    column_list = [CommentModel.id,
                   CommentModel.author_id,
                   CommentModel.parent_id,
                   CommentModel.post_id,
                   CommentModel.body,
                   CommentModel.created_at,
                   CommentModel.updated_at]
    
    form_include_pk = True
    
    # сделаем сортировку. True значит descending
    column_default_sort = [(CommentModel.created_at, True)]

    # запрет на редактирование полей
    form_excluded_columns = [CommentModel.id,
                             CommentModel.author_id,
                             CommentModel.created_at,
                             CommentModel.updated_at,
                             CommentModel.attachments,
                             CommentModel.author,
                             CommentModel.parent,
                             CommentModel.post]