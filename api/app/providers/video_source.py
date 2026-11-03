"""VideoSource provider interface and implementations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx


class VideoSource(ABC):
    @abstractmethod
    async def search(
        self, query: str, max_results: int = 25, **filters: Any
    ) -> List[Dict[str, Any]]:
        """Search videos and return candidate list."""
        ...

    @abstractmethod
    async def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch details (contentDetails, statistics, snippet) in batches."""
        ...


class YouTubeDataAPISource(VideoSource):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"

    async def search(
        self, query: str, max_results: int = 25, **filters: Any
    ) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        params = {
            "key": self.api_key,
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": min(max_results, 50),
        }
        params.update(filters)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/search", params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("items", [])

    async def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        if not self.api_key or not video_ids:
            return []
        results = []
        # Batch in chunks of 50
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            params = {
                "key": self.api_key,
                "id": ",".join(chunk),
                "part": "snippet,contentDetails,statistics",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/videos", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results.extend(data.get("items", []))
        return results


class FakeVideoSource(VideoSource):
    """Deterministic video provider for development, tests, and mock offline mode."""

    def __init__(self, fixtures: Optional[List[Dict[str, Any]]] = None) -> None:
        self.fixtures = fixtures or [
            {
                "id": "dQw4w9WgXcQ",
                "youtube_id": "dQw4w9WgXcQ",
                "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
                "description": "The official video for Never Gonna Give You Up by Rick Astley.",
                "source_channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
                "source_channel_title": "Rick Astley",
                "duration_s": 213,
                "is_short": False,
                "aspect": "landscape",
                "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"}},
                "published_at": "2009-10-25T06:57:33Z",
                "view_count": 1500000000,
                "like_count": 17000000,
            },
            {
                "id": "jNQXAC9IVRw",
                "youtube_id": "jNQXAC9IVRw",
                "title": "Me at the zoo",
                "description": "The first video on YouTube. #shorts",
                "source_channel_id": "UC4QobU6STFB0P71PMvOGN5A",
                "source_channel_title": "jawed",
                "duration_s": 19,
                "is_short": True,
                "aspect": "vertical",
                "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/jNQXAC9IVRw/hqdefault.jpg"}},
                "published_at": "2005-04-24T03:31:52Z",
                "view_count": 310000000,
                "like_count": 16000000,
            },
            {
                "id": "aircAruvnKk",
                "youtube_id": "aircAruvnKk",
                "title": "Neural Networks from Scratch - Introduction",
                "description": "Python neural network tutorial series.",
                "source_channel_id": "UCfzlCWGWYyIQZa_Ec44SUyg",
                "source_channel_title": "sentdex",
                "duration_s": 1045,
                "is_short": False,
                "aspect": "landscape",
                "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/aircAruvnKk/hqdefault.jpg"}},
                "published_at": "2020-04-09T18:00:10Z",
                "view_count": 1200000,
                "like_count": 55000,
            },
        ]

    async def search(
        self, query: str, max_results: int = 25, **filters: Any
    ) -> List[Dict[str, Any]]:
        return [
            {
                "id": {"videoId": item["youtube_id"]},
                "snippet": {
                    "title": item["title"],
                    "description": item["description"],
                    "channelId": item["source_channel_id"],
                    "channelTitle": item["source_channel_title"],
                    "publishedAt": item["published_at"],
                    "thumbnails": item["thumbnails"],
                },
            }
            for item in self.fixtures[:max_results]
        ]

    async def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        id_set = set(video_ids)
        return [
            {
                "id": item["youtube_id"],
                "snippet": {
                    "title": item["title"],
                    "description": item["description"],
                    "channelId": item["source_channel_id"],
                    "channelTitle": item["source_channel_title"],
                    "publishedAt": item["published_at"],
                    "thumbnails": item["thumbnails"],
                },
                "contentDetails": {
                    "duration": f"PT{item['duration_s']}S",
                },
                "statistics": {
                    "viewCount": str(item["view_count"]),
                    "likeCount": str(item["like_count"]),
                },
            }
            for item in self.fixtures
            if item["youtube_id"] in id_set
        ]
