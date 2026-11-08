# ==============================================================================
# VyapaarSetu Production Multi-Stage Dockerfile
# Builds both frontend React SPA and FastAPI backend into a single deployment
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Frontend Assets
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

# Install dependencies first for efficient layer caching
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source code and compile production bundles
COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Python Runtime & ASGI Server
# ------------------------------------------------------------------------------
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered standard I/O
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PORT=8000

WORKDIR /app

# Install system dependencies (curl for container health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend source code, migrations, tests, and configuration
COPY backend/ ./backend/

# Copy built frontend assets from Stage 1 into /app/frontend/dist
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

WORKDIR /app/backend

# Expose standard container port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8000}/api/v1/health || exit 1

# Apply database migrations, seed master FMCG catalogue, and launch Uvicorn on $PORT
CMD ["python", "-m", "app.scripts.start"]
