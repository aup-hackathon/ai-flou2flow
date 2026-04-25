FROM python:3.13-slim

WORKDIR /app

# Install uv for fast package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Install dependencies
RUN uv sync --frozen --no-install-project

# Copy application code
COPY flou2flow/ ./flou2flow/
COPY main.py ./

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "flou2flow.app:app", "--host", "0.0.0.0", "--port", "8000"]