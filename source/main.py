from fastapi import FastAPI
from source.routers.users import router as user_router
from source.routers.auth import router as auth_router
from source.routers.posts import router as post_router
from source.routers.uploads import router as upload_router
from source.routers.comments import router as comment_router
from fastapi.staticfiles import StaticFiles
import uvicorn
import argparse
from source.core.logger import default_logger
import logging


app = FastAPI()

app.include_router(user_router)
app.include_router(auth_router)
app.include_router(post_router)
app.include_router(comment_router)
app.include_router(upload_router)

# скачивание файлов
# пример: http://127.0.0.1:8000/uploads/filename.png
app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)



if __name__ == "__main__":
    print("main file")
    
    # параметры запуска
    parser = argparse.ArgumentParser()

    # уровень логирования приложения
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

    # если указан --uvicorn_reload, в reload_dirs помещает путь к файлам проекта
    # за измененями которых будет следить uvicorn
    # для корректной слежки, установлена библиотека watchfiles 
    uvicorn.run(
        "source.main:app",
        host="0.0.0.0",
        port=8000,
        reload=args.uvicorn_reload,
        reload_dirs=["/app/source"] if args.uvicorn_reload else None # явно указываем папку
    )