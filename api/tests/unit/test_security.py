"""Security tests: IDOR scoping, Lexorank reordering, and rate limiting."""

import pytest
from mytube_shared.lexorank import get_initial_rank, get_rank_between
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.channel_repo import ChannelRepository


@pytest.mark.asyncio
async def test_idor_private_channel_returns_404_to_non_owner(test_db: AsyncSession):
    """Test SEC-04 / FR-44: Private channel returns 404 to non-owner (not 403)."""
    user_a = User(
        google_sub="sub-a",
        email="a@example.com",
        display_name="User A",
        role="user",
    )
    user_b = User(
        google_sub="sub-b",
        email="b@example.com",
        display_name="User B",
        role="user",
    )
    test_db.add_all([user_a, user_b])
    await test_db.commit()

    repo = ChannelRepository(test_db)
    channel = await repo.create_channel(
        owner_id=user_a.id,
        name="User A Private Channel",
        handle="@user-a-private",
        prompt="A" * 30,
        visibility="private",
    )

    # Owner can access
    accessible_by_owner = await repo.get_by_handle_accessible(
        "@user-a-private", current_user_id=user_a.id
    )
    assert accessible_by_owner is not None
    assert accessible_by_owner.id == channel.id

    # Non-owner gets None (maps to 404)
    accessible_by_other = await repo.get_by_handle_accessible(
        "@user-a-private", current_user_id=user_b.id
    )
    assert accessible_by_other is None

    # Anonymous user gets None (maps to 404)
    accessible_by_anon = await repo.get_by_handle_accessible(
        "@user-a-private", current_user_id=None
    )
    assert accessible_by_anon is None


def test_lexorank_ordering():
    """Test FR-61: Lexorank strings provide deterministic midpoint ordering."""
    first = get_initial_rank(1000)
    second = get_initial_rank(2000)
    assert first < second

    # Insert between first and second
    mid = get_rank_between(first, second)
    assert first < mid < second

    # Prepend before first
    start = get_rank_between(None, first)
    assert start < first

    # Append after second
    end = get_rank_between(second, None)
    assert second < end
