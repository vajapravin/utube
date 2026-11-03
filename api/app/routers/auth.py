"""Authentication router handling Google OIDC BFF flow, PKCE, and session rotation."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.deps import (
    check_csrf,
    get_current_user,
    get_db,
    get_rate_limiter,
    get_redis,
    get_session_manager,
)
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.user_repo import UserRepository
from app.security.csrf import generate_csrf_token, set_csrf_cookie
from app.security.oidc import OIDCService
from app.security.rate_limit import RateLimiter
from app.security.sessions import COOKIE_NAME, SessionManager

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/login", summary="Initiate Google OIDC login with PKCE")
async def login(
    request: Request,
    settings: Settings = Depends(get_settings),
    redis_client: aioredis.Redis = Depends(get_redis),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> RedirectResponse:
    # Rate limit: 20 login attempts per min per IP (SEC-06)
    client_ip = request.client.host if request.client else "127.0.0.1"
    await rate_limiter.check_rate_limit(
        f"auth_login:{client_ip}", max_requests=20, window_seconds=60
    )

    oidc = OIDCService(redis_client)
    redirect_uri = f"{settings.PUBLIC_BASE_URL}/api/v1/auth/callback"
    auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"

    # Test mode with mock-oidc
    if settings.APP_ENV == "test":
        auth_endpoint = f"http://localhost:{settings.MOCK_OIDC_PORT}/default/authorize"

    params = await oidc.create_authorization_params(
        client_id=settings.GOOGLE_CLIENT_ID or "mock-client-id",
        redirect_uri=redirect_uri,
        auth_endpoint=auth_endpoint,
    )
    return RedirectResponse(url=params["authorization_url"], status_code=status.HTTP_302_FOUND)


@router.get("/callback", summary="Google OIDC callback endpoint")
async def callback(
    request: Request,
    response: Response,
    code: str = Query(...),
    state: str = Query(...),
    settings: Settings = Depends(get_settings),
    redis_client: aioredis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
    session_mgr: SessionManager = Depends(get_session_manager),
) -> RedirectResponse:
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent")
    audit_repo = AuditRepository(db)
    user_repo = UserRepository(db)
    oidc = OIDCService(redis_client)

    token_endpoint = "https://oauth2.googleapis.com/token"
    test_mode = settings.APP_ENV == "test"
    if test_mode:
        token_endpoint = f"http://localhost:{settings.MOCK_OIDC_PORT}/default/token"

    try:
        user_info = await oidc.validate_callback(
            code=code,
            state=state,
            client_id=settings.GOOGLE_CLIENT_ID or "mock-client-id",
            client_secret=settings.GOOGLE_CLIENT_SECRET or "mock-secret",
            token_endpoint=token_endpoint,
            test_mode=test_mode,
        )
    except Exception as exc:
        await audit_repo.log_event(
            action="auth.login.failure",
            ip_address=client_ip,
            user_agent=user_agent,
            meta={"error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth verification failed: {exc}",
        )

    # 1. Allow-list verification (FR-03)
    user_email = user_info.email.lower()
    email_domain = user_email.split("@")[-1] if "@" in user_email else ""
    allowed = (
        settings.OPEN_REGISTRATION
        or (user_email in settings.allowed_email_list)
        or (email_domain in settings.allowed_domain_list)
    )

    if not allowed:
        await audit_repo.log_event(
            action="auth.allowlist.denied",
            ip_address=client_ip,
            user_agent=user_agent,
            meta={"email": user_email},
        )
        # Redirect to access-not-enabled screen
        return RedirectResponse(
            url=f"{settings.PUBLIC_BASE_URL}/access-denied",
            status_code=status.HTTP_302_FOUND,
        )

    # 2. Upsert user in database (FR-02)
    user, is_new = await user_repo.upsert_from_google(
        sub=user_info.sub,
        email=user_email,
        display_name=user_info.name,
        avatar_url=user_info.picture,
    )

    # 3. Create Redis session with 256-bit ID (FR-04)
    session_id = await session_mgr.create_session(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    # 4. Generate CSRF token (FR-05)
    csrf_token = generate_csrf_token()

    # 5. Determine redirect target
    target_path = "/onboarding" if is_new or not user.onboarded_at else "/"
    redirect_url = f"{settings.PUBLIC_BASE_URL}{target_path}"

    redirect_resp = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    # Set __Host- session cookie
    redirect_resp.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
        max_age=30 * 24 * 3600,
    )

    # Set readable CSRF cookie
    set_csrf_cookie(redirect_resp, csrf_token, secure=settings.is_production)

    await audit_repo.log_event(
        action="auth.login.success",
        ip_address=client_ip,
        actor_id=user.id,
        user_agent=user_agent,
        meta={"is_new": is_new},
    )
    return redirect_resp


@router.post("/logout", summary="Sign out active session", dependencies=[Depends(check_csrf)])
async def logout(
    request: Request,
    response: Response,
    session_mgr: SessionManager = Depends(get_session_manager),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    session_id = request.cookies.get(COOKIE_NAME)
    if session_id:
        await session_mgr.delete_session(session_id)

    response.delete_cookie(key=COOKIE_NAME, path="/")
    response.delete_cookie(key="mytube_csrf", path="/")

    client_ip = request.client.host if request.client else "127.0.0.1"
    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        action="auth.logout",
        ip_address=client_ip,
        actor_id=current_user.id,
    )
    return {"status": "logged_out"}


@router.post("/logout-all", summary="Sign out all devices", dependencies=[Depends(check_csrf)])
async def logout_all(
    request: Request,
    response: Response,
    session_mgr: SessionManager = Depends(get_session_manager),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await session_mgr.delete_all_user_sessions(current_user.id)
    response.delete_cookie(key=COOKIE_NAME, path="/")
    response.delete_cookie(key="mytube_csrf", path="/")

    client_ip = request.client.host if request.client else "127.0.0.1"
    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        action="auth.logout_all",
        ip_address=client_ip,
        actor_id=current_user.id,
    )
    return {"status": "all_sessions_revoked"}
