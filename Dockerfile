# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build-only

FROM python:3.13-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static \
    SQLITE_PATH=/app/data/puzzles.db

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /fe/dist ./static

RUN mkdir -p /var/data /app/data

EXPOSE 8081
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8081}"]
