"""OIDC Authentication flow with PKCE, state, and nonce verification."""

import base64
import hashlib
import json
import secrets
from typing import Dict, Optional

import httpx
import redis.asyncio as aioredis
from pydantic import BaseModel


class OIDCUserInfo(BaseModel):
    sub: str
    email: str
    name: str
    picture: Optional[str] = None
    email_verified: bool = False
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class OIDCService:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self.redis = redis_client

    def _generate_code_verifier(self) -> str:
        return secrets.token_urlsafe(64)

    def _generate_code_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    async def create_authorization_params(
        self,
        client_id: str,
        redirect_uri: str,
        auth_endpoint: str,
        scope: str = "openid email profile https://www.googleapis.com/auth/youtube.readonly",
    ) -> Dict[str, str]:
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = self._generate_code_verifier()
        challenge = self._generate_code_challenge(verifier)

        # Store auth state in Redis with 10-minute TTL
        state_data = {
            "state": state,
            "nonce": nonce,
            "verifier": verifier,
            "redirect_uri": redirect_uri,
        }
        await self.redis.set(f"oidc_state:{state}", json.dumps(state_data), ex=600)

        import urllib.parse
        encoded_scope = urllib.parse.quote(scope)

        url = (
            f"{auth_endpoint}"
            f"?response_type=code"
            f"&client_id={client_id}"
            f"&scope={encoded_scope}"
            f"&access_type=offline"
            f"&prompt=consent"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
            f"&nonce={nonce}"
            f"&code_challenge={challenge}"
            f"&code_challenge_method=S256"
        )
        return {"authorization_url": url, "state": state}

    async def validate_callback(
        self,
        code: str,
        state: str,
        client_id: str,
        client_secret: str,
        token_endpoint: str,
        jwks_endpoint: Optional[str] = None,
        test_mode: bool = False,
    ) -> OIDCUserInfo:
        # Retrieve state from Redis
        state_key = f"oidc_state:{state}"
        raw = await self.redis.get(state_key)
        if not raw:
            raise ValueError("Invalid or expired OAuth state parameter")
        await self.redis.delete(state_key)

        state_data = json.loads(raw)
        verifier = state_data["verifier"]
        expected_nonce = state_data["nonce"]
        redirect_uri = state_data["redirect_uri"]

        # Exchange code for tokens
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code_verifier": verifier,
                },
            )
            if token_resp.status_code != 200:
                raise ValueError(f"Token exchange failed: {token_resp.text}")

            tokens = token_resp.json()
            id_token = tokens.get("id_token")
            access_token = tokens.get("access_token")

            # Parse ID token payload (header.payload.signature)
            if id_token:
                parts = id_token.split(".")
                if len(parts) >= 2:
                    padded = parts[1] + "=" * (-len(parts[1]) % 4)
                    payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))

                    # Nonce validation
                    if payload.get("nonce") != expected_nonce:
                        raise ValueError("ID token nonce mismatch")

                    email = payload.get("email")
                    sub = payload.get("sub")
                    name = payload.get("name", email.split("@")[0] if email else "User")
                    picture = payload.get("picture")
                    email_verified = payload.get("email_verified", True if test_mode else False)

                    if not email_verified:
                        raise ValueError("Email address is not verified by identity provider")

                    return OIDCUserInfo(
                        sub=str(sub),
                        email=email,
                        name=name,
                        picture=picture,
                        email_verified=email_verified,
                        access_token=access_token,
                        refresh_token=refresh_token,
                    )

            # Fallback to UserInfo endpoint if access_token available
            if access_token:
                userinfo_resp = await client.get(
                    token_endpoint.replace("/token", "/userinfo"),
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if userinfo_resp.status_code == 200:
                    info = userinfo_resp.json()
                    return OIDCUserInfo(
                        sub=str(info["sub"]),
                        email=info["email"],
                        name=info.get("name", info["email"]),
                        picture=info.get("picture"),
                        email_verified=info.get("email_verified", False),
                        access_token=access_token,
                        refresh_token=refresh_token,
                    )

        raise ValueError("Could not extract user identity from OIDC provider")
