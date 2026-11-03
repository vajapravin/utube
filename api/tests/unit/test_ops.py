"""Unit tests for operations and observability endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz_endpoint(client: AsyncClient):
    """Test NFR-06: /healthz returns status ok."""
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz_endpoint(client: AsyncClient):
    """Test NFR-06: /readyz checks DB and Redis."""
    resp = await client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    """Test NFR-06: /metrics returns prometheus metrics."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "process_cpu_seconds_total" in resp.text or "# HELP" in resp.text
