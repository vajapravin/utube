"""Cross-Site Request Forgery (CSRF) protection using double-submit cookies."""

import secrets
from urllib.parse import urlparse

from fastapi import HTTPException, Request, Response, status

CSRF_COOKIE_NAME = "mytube_csrf"
CSRF_HEADER_NAME = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def generate_csrf_token() -> str:
    """Generate a random 32-byte URL-safe CSRF token."""
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str, secure: bool = True) -> None:
    """Set readable CSRF cookie for client-side JavaScript."""
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # Client needs to read and echo in X-CSRF-Token header
        secure=secure,
        samesite="lax",
        path="/",
    )


def verify_csrf(request: Request, public_base_url: str) -> None:
    """Verify double-submit CSRF token and origin for state-changing HTTP requests."""
    if request.method in SAFE_METHODS:
        return

    # 1. Verify Origin / Referer against PUBLIC_BASE_URL
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    expected_netloc = urlparse(public_base_url).netloc

    check_url = origin or referer
    if check_url:
        parsed = urlparse(check_url)
        if parsed.netloc and parsed.netloc != expected_netloc:
            # Allow localhost / dev origin in non-production
            if not ("localhost" in parsed.netloc or "127.0.0.1" in parsed.netloc):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Origin/Referer header does not match expected host",
                )

    # 2. Check double-submit cookie & header
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if not cookie_token or not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing CSRF cookie or X-CSRF-Token header",
        )

    if not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token match",
        )
