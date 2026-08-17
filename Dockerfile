# Используем легкий официальный образ Python
FROM python:3.14-slim

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Запрещаем Python создавать файлы .pyc и включаем буферизацию вывода 
# (чтобы логи Celery сразу попадали в консоль)
# укаызываем явно путь к виртуальному окружению где uv установит пакеты
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файлы конфигурации uv
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости (они будут установлены в системный python)
# --no-install-project - не устанавливает сам код проекта, только зависимости
# код проекта скопируется в следующей команде
RUN uv sync --frozen --no-install-project

# Копируем исходный код бекенда, папку с логами и конфиг миграций
#COPY . .
COPY alembic.ini ./
COPY source/ ./source/
COPY logs/ ./logs/
