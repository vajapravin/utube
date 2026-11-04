from unittest.mock import AsyncMock, MagicMock

import pytest

from app.jobs import refresh_categories_job


@pytest.mark.asyncio
async def test_refresh_categories_job():
    ctx = {
        "session_factory": MagicMock(),
        "video_source": MagicMock(),
    }
    # Video source search returns mock candidates
    ctx["video_source"].search = AsyncMock(return_value=[{"id": {"videoId": "test12345"}}])
    ctx["video_source"].get_video_details = AsyncMock(
        return_value=[
            {
                "id": "test12345",
                "snippet": {
                    "title": "Test Title",
                    "description": "Test Description",
                    "channelId": "UC123",
                    "channelTitle": "Test Channel",
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "thumbnails": {
                        "high": {"url": "https://img.youtube.com/vi/test12345/hqdefault.jpg"}
                    },
                },
                "contentDetails": {"duration": "PT5M30S"},
                "statistics": {"viewCount": "1000", "likeCount": "100"},
            }
        ]
    )

    # Mock DB session
    session = AsyncMock()
    mock_cat = MagicMock()
    mock_cat.id = "00000000-0000-0000-0000-000000000001"
    mock_cat.name = "Programming"
    mock_cat.seed_queries = ["python tutorial"]

    scalar_res = MagicMock()
    scalar_res.scalars.return_value.all.return_value = [mock_cat]

    vid_res = MagicMock()
    vid_res.scalar_one.return_value = "00000000-0000-0000-0000-000000000002"

    session.execute = AsyncMock(side_effect=[scalar_res, vid_res, MagicMock()])
    session.commit = AsyncMock()

    class SessionCtx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    ctx["session_factory"].return_value = SessionCtx()

    total = await refresh_categories_job(ctx)
    assert total == 1
    session.commit.assert_awaited_once()
