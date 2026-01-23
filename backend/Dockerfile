# syntax=docker/dockerfile:1
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    libgl1 \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# Constants
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# copy and install dependencies only to cache them
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,id=s/f12344f9-b197-42d2-acfc-0048905a93c8-/root/cache/uv,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY src/ ./src/

# install dependencies
RUN --mount=type=cache,id=s/f12344f9-b197-42d2-acfc-0048905a93c8-/root/cache/uv,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Create directory for ChromaDB
RUN mkdir -p /app/chroma_db

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]