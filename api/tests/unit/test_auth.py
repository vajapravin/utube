"""Unit tests for authentication, OIDC PKCE flow, and allow-list enforcement."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_login_redirect_has_pkce(client: AsyncClient, mock_redis):
    """Test FR-01: Login initiates PKCE with state, nonce, and code_challenge."""
    resp = await client.get("/api/v1/auth/login", follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]

    assert "response_type=code" in location
    assert "code_challenge=" in location
    assert "code_challenge_method=S256" in location
    assert "state=" in location
    assert "nonce=" in location


@pytest.mark.asyncio
async def test_auth_callback_rejects_missing_state(client: AsyncClient):
    """Test FR-01 AC: Callback rejects unknown or tampered state."""
    resp = await client.get("/api/v1/auth/callback?code=mock-code&state=nonexistent-state")
    assert resp.status_code == 400
    assert "OAuth verification failed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_csrf_protection_on_post_without_token(client: AsyncClient):
    """Test FR-05: State-changing POST without CSRF header is rejected with 403."""
    resp = await client.post("/api/v1/channels", json={"name": "Test", "prompt": "A" * 30})
    assert resp.status_code == 403
    assert "Missing CSRF" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_csrf_protection_with_valid_matching_token(client: AsyncClient):
    """Test FR-05: State-changing POST with matching token and cookie passes CSRF."""
    token = "valid-csrf-token-12345678901234567890"
    resp = await client.post(
        "/api/v1/channels",
        json={"name": "Test", "prompt": "A" * 30},
        cookies={"mytube_csrf": token},
        headers={"X-CSRF-Token": token},
    )
    # Passes CSRF check and reaches authentication check -> returns 401
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]
