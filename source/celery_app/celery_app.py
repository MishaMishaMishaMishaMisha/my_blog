import os

from celery import Celery

from source.core.config import settings
from source.core.logger import default_logger


print("celery_app file>")


app = Celery("source.celery_app.celery_app",
             broker=settings.redis.url,
             backend=settings.redis.url,
             include=["source.tasks.email_task",
                      "source.tasks.views_count_task",
                      "source.tasks.delete_mediafiles_task"],
             broker_connection_retry_on_startup=True)

"""
Аргументы:
- название модуля (полный путь) где лежит этот объект app
- broker адрес для подключения к брокеру. тут это "redis://redis:6379/0"
- backend место где будет сохранен результат выполнения задачи. тут указан тоже Redis
- inclue список модулей с задачами
- последний параметр нужен просто чтобы не было предупреждений в консоли
"""

# Если режим TEST или CELERY_TASK_ALWAYS_EAGER=True, задачи выполняются синхронно
if os.getenv("MODE") == "TEST" or os.getenv("CELERY_TASK_ALWAYS_EAGER") == "True":
    default_logger.debug("setting celery task eager = True")
    app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True, # Бросает исключение прямо в тесте, если задача упала
    )

else:
    
    default_logger.debug("setting schedule for tasks")
    
    # делаем периодичными задачи:
    # по обновлению views_count в постах - каждые 5 минут
    # по удалению неиспользованных файлов - раз в день
    # по синхронизации файлов в хранилище и бд - раз в день
    app.conf.beat_schedule = {
        "sync-post-views": {
            "task": "source.tasks.views_count_task.update_views_count",
            "schedule": 300,
        },
        "delete-temp-files": {
            "task": "source.tasks.delete_mediafiles_task.delete_temp_files",
            "schedule": 86400,
        },
        "sync-files": {
            "task": "source.tasks.delete_mediafiles_task.sync_Files_in_Storage_and_in_DB",
            "schedule": 86400,
        },
    }
    
    
    