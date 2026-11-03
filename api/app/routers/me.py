"""User profile, settings, interests, and GDPR deletion router."""

from typing import List, Sequence

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import check_csrf, get_current_user, get_db, get_session_manager
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.category_repo import CategoryRepository
from app.repositories.user_repo import UserRepository
from app.repositories.video_repo import VideoRepository
from app.schemas.category import CategoryResponse, UserInterestsUpdate
from app.schemas.common import CursorPage
from app.schemas.user import DeleteAccountRequest, UserProfile, UserSettingsUpdate
from app.schemas.video import VideoResponse
from app.security.sessions import COOKIE_NAME, SessionManager

router = APIRouter(prefix="/me", tags=["Profile & Settings"])


@router.get("", response_model=UserProfile, summary="Get current user profile")
async def get_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch(
    "",
    response_model=UserProfile,
    summary="Update user preferences",
    dependencies=[Depends(check_csrf)],
)
async def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_repo = UserRepository(db)
    updated = await user_repo.update_settings(current_user, payload.model_dump(exclude_unset=True))
    return updated


@router.delete("", summary="GDPR right to erasure", dependencies=[Depends(check_csrf)])
async def delete_account(
    request: Request,
    response: Response,
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    session_mgr: SessionManager = Depends(get_session_manager),
) -> dict[str, str]:
    if payload.confirm_email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation email does not match user account email",
        )

    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Soft-delete user row (and cascade dependencies)
    await user_repo.soft_delete(current_user)

    # 2. Revoke all active sessions
    await session_mgr.delete_all_user_sessions(current_user.id)
    response.delete_cookie(key=COOKIE_NAME, path="/")
    response.delete_cookie(key="mytube_csrf", path="/")

    # 3. Log audit event
    await audit_repo.log_event(
        action="account.deleted",
        ip_address=client_ip,
        actor_id=current_user.id,
        meta={"email": current_user.email},
    )
    return {"status": "account_deleted"}


@router.get(
    "/interests", response_model=List[CategoryResponse], summary="Get chosen interest categories"
)
async def get_interests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Sequence[CategoryResponse]:
    cat_repo = CategoryRepository(db)
    interests = await cat_repo.get_user_interests(current_user.id)
    return [CategoryResponse.model_validate(c) for c in interests]


@router.put(
    "/interests",
    response_model=List[CategoryResponse],
    summary="Update interest categories",
    dependencies=[Depends(check_csrf)],
)
async def update_interests(
    payload: UserInterestsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Sequence[CategoryResponse]:
    cat_repo = CategoryRepository(db)
    user_repo = UserRepository(db)

    # Persist chosen categories (FR-11)
    await cat_repo.set_user_interests(current_user.id, payload.category_ids)
    if not current_user.onboarded_at:
        await user_repo.complete_onboarding(current_user)

    interests = await cat_repo.get_user_interests(current_user.id)
    return [CategoryResponse.model_validate(c) for c in interests]


@router.get(
    "/likes", response_model=CursorPage[VideoResponse], summary="List all videos liked by user"
)
async def get_my_likes(
    limit: int = 24,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CursorPage[VideoResponse]:
    video_repo = VideoRepository(db)
    videos = await video_repo.get_user_likes(current_user.id, limit=limit)
    items = [
        VideoResponse.model_validate({**v.__dict__, "is_liked": True, "is_saved": False})
        for v in videos
    ]
    return CursorPage(items=items, next_cursor=None, has_more=False)
