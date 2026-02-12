# ========== Stage 1: Build Frontend ==========
FROM node:22-slim AS frontend-build

WORKDIR /app/frontend

# Install dependencies first (cache layer)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --force

# Build frontend
COPY frontend/ ./
RUN npm run build

# ========== Stage 2: Python Backend ==========
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy Python project files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY src/ ./src/
COPY data/ ./data/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Environment defaults
ENV HOST=0.0.0.0
ENV PORT=8000
ENV SERVE_STATIC=true
ENV UV_CACHE_DIR=/tmp/.uv-cache

# Create non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

# Run with uvicorn via uv (UV_CACHE_DIR set to writable /tmp)
CMD ["uv", "run", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
