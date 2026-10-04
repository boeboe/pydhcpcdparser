# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm AS base

WORKDIR /app

# Install build tools
RUN pip install --no-cache-dir hatchling

# Copy dependency metadata first for better caching
# README.md is required by hatchling metadata validation
COPY pyproject.toml README.md ./

# Create minimal source layout so pip install can resolve the package
RUN mkdir -p src/pydhcpcdparser && touch src/pydhcpcdparser/__init__.py

# Install dependencies only (not the real source yet)
RUN pip install --no-cache-dir ".[dev]"

# Copy source code
COPY . .

# Reinstall with real source
RUN pip install --no-cache-dir ".[dev]"

# Default command
CMD ["python", "-c", "import pydhcpcdparser; print(f'pydhcpcdparser {pydhcpcdparser.__version__}')"]

# Test stage
FROM base AS test
CMD ["pytest", "-v"]

# Lint stage
FROM base AS lint
CMD ["sh", "-c", "ruff check src/ tests/ && mypy src/"]
