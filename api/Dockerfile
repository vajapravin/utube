FROM python:3.12-slim AS builder

WORKDIR /build

COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /usr/local/bin/uv

COPY shared/py /build/shared/py
COPY api/pyproject.toml /build/api/pyproject.toml

WORKDIR /build/api
RUN uv pip install --no-cache --system /build/shared/py && uv pip install --no-cache --system --no-sources .

FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 10001 mytube && useradd -u 10001 -g mytube -m -s /bin/bash mytube

WORKDIR /app
ENV PYTHONPATH="/app"

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY shared/py/mytube_shared /app/mytube_shared
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
