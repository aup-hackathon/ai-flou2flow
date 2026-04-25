# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Install curl for docker-compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Install dependencies (without dev dependencies)
RUN uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY flou2flow/ ./flou2flow/
COPY main.py ./

# Sync project (optional but good practice to install the project itself if needed)
RUN uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Run the application using the uvicorn installed in the virtual environment
CMD ["uvicorn", "flou2flow.app:app", "--host", "0.0.0.0", "--port", "8000"]
