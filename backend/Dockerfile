# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install system runtime dependencies for PDF rendering and OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official binary image
COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/
COPY ml/pyproject.toml ml/

# Install backend dependencies without dev tools
RUN uv sync --frozen --no-dev --package invoice-backend

# Copy backend source code and migrations
COPY backend/app ./backend/app
COPY backend/alembic ./backend/alembic
COPY backend/alembic.ini ./backend/alembic.ini
COPY .env.example ./.env

ENV PYTHONPATH="/app/backend:/app"
ENV INVOICE_MODELS_DIR="/app/models"
ENV PORT=8000

EXPOSE 8000

WORKDIR /app/backend
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
