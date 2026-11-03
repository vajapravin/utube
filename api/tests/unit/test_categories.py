"""Unit tests for categories catalogue and onboarding rules."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, test_db: AsyncSession):
    """Test FR-10: List active categories catalogue."""
    cat = Category(
        slug="ai-ml",
        name="AI & Machine Learning",
        icon="brain",
        seed_queries=["python ai"],
        sort_order=1,
        is_active=True,
    )
    test_db.add(cat)
    await test_db.commit()

    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert any(c["slug"] == "ai-ml" for c in items)
