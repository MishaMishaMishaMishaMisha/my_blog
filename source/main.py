from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware

from source.api.v1.routers.api_v1_router import api_v1_router
from source.cache.redis_backend import redis_backend
from source.core.logger import default_logger
from source.core.types import STORAGE_PATH
from source.core.config import settings
from source.database.db_connect import async_session_factory
from source.admin.init_admin import create_first_admin
from source.admin import register_admin_views
from source.admin.auth_admin import AdminAuth


# Убеждаемся, что папка /uploads существует при старте приложения
STORAGE_PATH.mkdir(parents=True, exist_ok=True)

def create_app(with_lifespan: bool = True) -> FastAPI:
    
    if with_lifespan:
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            
            await redis_backend.init_rate_limiter()
            
            await create_first_admin()
            
            yield
            
            await redis_backend.close()

        app = FastAPI(lifespan=lifespan)
        
    else:
        app = FastAPI()
        
    app.include_router(api_v1_router)

    # CORS - позволить фронтенду делать запросы к бекенду
    # изменено на адрес nginx
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://localhost:80"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # middleware для использования сессий в админке
    app.add_middleware(SessionMiddleware,
                       secret_key=settings.ADMIN_SECRET_KEY)
        
    # админка
    admin_auth = AdminAuth(secret_key=settings.ADMIN_SECRET_KEY)
    admin = Admin(app=app, 
                  session_maker=async_session_factory,
                  authentication_backend=admin_auth)
    register_admin_views(admin)

    return app

app = create_app()




if __name__ == "__main__":
    print("<main file>")
    