FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv for fast, reproducible dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /usr/local/bin/uv

# Copy pyproject and shared libraries
COPY shared/py /build/shared/py
COPY api/pyproject.toml /build/api/pyproject.toml

WORKDIR /build/api
RUN uv pip install --no-cache --system .

# Production runtime stage
FROM python:3.12-slim AS runtime

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Run as unprivileged non-root user (UID 10001)
RUN groupadd -g 10001 mytube && useradd -u 10001 -g mytube -m -s /bin/bash mytube

WORKDIR /app

# Copy installed site-packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source code
COPY api/app /app/app
COPY api/migrations /app/migrations
COPY api/alembic.ini /app/alembic.ini
COPY seed /app/seed

RUN chown -R mytube:mytube /app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 --start-period=5s \
  CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
