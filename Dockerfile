# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm AS base

WORKDIR /app

# Install build tools
RUN pip install --no-cache-dir hatchling

# Copy dependency metadata first for better caching
COPY pyproject.toml ./

# Install the package with dev dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source code
COPY . .

# Reinstall with source
RUN pip install --no-cache-dir -e ".[dev]"

# Default command
CMD ["python", "-c", "import pydhcpcdparser; print(f'pydhcpcdparser {pydhcpcdparser.__version__}')"]

# Test stage
FROM base AS test
CMD ["pytest", "-v"]

# Lint stage
FROM base AS lint
CMD ["sh", "-c", "ruff check src/ tests/ && mypy src/"]
