from sqladmin import Admin

from source.admin.user import UserAdmin
from source.admin.tag import TagAdmin
from source.admin.post import PostAdmin
from source.admin.comment import CommentAdmin

def register_admin_views(admin: Admin):
    admin.add_view(UserAdmin)
    admin.add_view(TagAdmin)
    admin.add_view(PostAdmin)
    admin.add_view(CommentAdmin)