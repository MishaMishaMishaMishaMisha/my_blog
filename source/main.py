import uvicorn
import argparse
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from source.api.v1.routers.api_v1_router import api_v1_router
from source.cache.redis_backend import redis_backend
from source.core.logger import default_logger
from source.core.types import STORAGE_PATH
from source.database.init_admin import create_first_admin


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
    
    # скачивание файлов
    # пример: http://127.0.0.1:8000/api/v1/app/uploads/filename.png
    app.mount(
        "/api/v1/app/uploads",
        StaticFiles(directory=str(STORAGE_PATH)),
        name="uploads"
    )

    # CORS - позволить фронтенду делать запросы к бекенду
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app

app = create_app()




if __name__ == "__main__":
    print("<main file>")
    
    # параметры запуска
    parser = argparse.ArgumentParser()

    # уровень логирования приложения
    # пример --app_log_level INFO
    parser.add_argument(
        "--app_log_level",
        default="DEBUG",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="App logging level",
    )
    
    # автоматическая перезагрузка uvicorn 
    # если параметр --uvicorn_reload не указан - False
    # если указан - True
    parser.add_argument(
        "--uvicorn_reload",
        action="store_true",
        help="Enable auto reload"
    )
    
    args = parser.parse_args()
    
    print("App executed with parameters: ")
    print("app-log-level=", args.app_log_level)
    print("uvicorn-reload=", args.uvicorn_reload)

    default_logger.setLevel(logging._nameToLevel[args.app_log_level])

    # если указан --uvicorn_reload, в reload_dirs указываем путь к файлам проекта
    # за измененями которых будет следить uvicorn
    # для корректной слежки, установлена библиотека watchfiles 
    uvicorn.run(
        "source.main:app",
        host="0.0.0.0",
        port=8000,
        reload=args.uvicorn_reload,
        reload_dirs=["/app/source"] if args.uvicorn_reload else None
    )