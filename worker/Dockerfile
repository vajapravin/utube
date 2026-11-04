FROM python:3.12-slim AS builder

WORKDIR /build

COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /usr/local/bin/uv

COPY shared/py /build/shared/py
COPY api/pyproject.toml /build/api/pyproject.toml
COPY worker/pyproject.toml /build/worker/pyproject.toml

WORKDIR /build/worker
RUN uv pip install --no-cache --system /build/shared/py && uv pip install --no-cache --system --no-sources .

FROM python:3.12-slim AS runtime

RUN groupadd -g 10001 mytube && useradd -u 10001 -g mytube -m -s /bin/bash mytube

WORKDIR /app
ENV PYTHONPATH="/app"

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY shared/py/mytube_shared /app/mytube_shared
COPY worker/app /app/app
COPY api/app/models /app/app/models
COPY api/app/schemas /app/app/schemas
COPY api/app/providers /app/app/providers

RUN chown -R mytube:mytube /app

USER 10001:10001

CMD ["python", "-m", "arq", "app.jobs.ArqWorkerSettings"]
