# Используем легкий официальный образ Python
FROM python:3.14-slim

# Запрещаем Python создавать файлы .pyc и включаем буферизацию вывода (чтобы логи Celery сразу попадали в консоль)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Сначала копируем только файл зависимостей, чтобы эффективнее использовать кэш Docker
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь исходный код проекта
COPY . .