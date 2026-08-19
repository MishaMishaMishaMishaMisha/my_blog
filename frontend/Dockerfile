# --- Stage 1: Build ---
FROM node:20-alpine AS build-stage

WORKDIR /app

# Копируем манифесты зависимостей для эффективного кэширования слоев
COPY package*.json ./

# Устанавливаем зависимости
RUN npm ci

# Копируем исходный код и собираем проект
COPY . .
RUN npm run build

# --- Stage 2: Production ---
FROM nginx:alpine AS production-stage

# Копируем собранную статику из первого этапа в директорию Nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Копируем пользовательскую конфигурацию Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]