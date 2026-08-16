from source.api.v1.routers.users import router as user_router
from source.api.v1.routers.auth import router as auth_router
from source.api.v1.routers.posts import router as post_router
from source.api.v1.routers.uploads import router as upload_router
from source.api.v1.routers.comments import router as comment_router

from fastapi import APIRouter


api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(user_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(post_router)
api_v1_router.include_router(comment_router)
api_v1_router.include_router(upload_router)