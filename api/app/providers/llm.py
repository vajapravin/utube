"""LLM Provider abstraction and implementations."""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger("mytube.llm")


class LLMProvider(ABC):
    @abstractmethod
    async def generate_structured(
        self,
        system: str,
        user: str,
        schema: Type[T],
        *,
        temperature: float = 0.2,
    ) -> T:
        """Generate structured output validated against a Pydantic schema."""
        ...


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        )

    async def generate_structured(
        self,
        system: str,
        user: str,
        schema: Type[T],
        *,
        temperature: float = 0.2,
    ) -> T:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        url = f"{self.base_url}?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "response_mime_type": "application/json",
                "response_schema": schema.model_json_schema(),
            },
        }

        # Exponential backoff retry loop (max 3 tries)
        for attempt in range(1, 4):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        return schema.model_validate_json(text)
                    elif resp.status_code in (429, 503):
                        wait = (2**attempt) + random.uniform(0.1, 0.5)
                        logger.warning(
                            "Gemini rate limited (%s), retrying in %.2fs", resp.status_code, wait
                        )
                        await asyncio.sleep(wait)
                    else:
                        raise ValueError(
                            f"Gemini API returned status {resp.status_code}: {resp.text}"
                        )
            except httpx.RequestError:
                if attempt == 3:
                    raise
                await asyncio.sleep(1.0)

        raise RuntimeError("Failed to generate structured response from Gemini after 3 attempts")


class FakeLLMProvider(LLMProvider):
    """Deterministic LLM mock for unit tests and local mock curation."""

    async def generate_structured(
        self,
        system: str,
        user: str,
        schema: Type[T],
        *,
        temperature: float = 0.2,
    ) -> T:
        import json
        import re

        schema_name = schema.__name__
        if "ChannelPlan" in schema_name:
            from mytube_shared.guardrails import build_career_focused_queries

            m = re.search(r"<user_prompt>(.*?)</user_prompt>", user, re.DOTALL)
            prompt_text = m.group(1).strip() if m else ""
            queries = build_career_focused_queries(prompt_text)

            clean_prompt = re.sub(r"[^\w\s]", " ", prompt_text).strip()
            words = [w for w in clean_prompt.split() if len(w) > 2]

            data = {
                "queries": queries,
                "must_include_terms": [],
                "exclude_terms": ["clickbait", "reaction", "prank", "funny", "comedy", "meme", "tiktok"],
                "language": "en",
                "region": "GB",
                "min_duration_s": 60,
                "max_duration_s": 3600,
                "safe_search": "strict",
                "want_shorts": True,
                "want_videos": True,
            }
            return schema.model_validate(data)

        # Candidate ranking mock
        if "RankBatchResult" in schema_name or "Rank" in schema_name:
            from mytube_shared.guardrails import evaluate_career_relevance

            m_user = re.search(r"<user_prompt>(.*?)</user_prompt>", user, re.DOTALL)
            prompt_text = m_user.group(1).strip() if m_user else ""

            results = []
            m = re.search(r"<candidates>(.*?)</candidates>", user, re.DOTALL)
            if m:
                try:
                    candidates_data = json.loads(m.group(1))
                    for c in candidates_data:
                        score = evaluate_career_relevance(prompt_text, c)
                        kind = "short" if c.get("duration_s", 0) <= 180 else "video"
                        results.append(
                            {
                                "id": c.get("id"),
                                "relevance_score": score,
                                "kind": kind,
                                "reason": f"Career relevance: {score}/100",
                            }
                        )
                except Exception:
                    pass

            if not results:
                results = [
                    {
                        "id": "dQw4w9WgXcQ",
                        "relevance_score": 85,
                        "kind": "video",
                        "reason": "Matches core interest well with high clarity.",
                    },
                    {
                        "id": "jNQXAC9IVRw",
                        "relevance_score": 75,
                        "kind": "short",
                        "reason": "Historic short clip matching interest.",
                    },
                ]
            return schema.model_validate({"results": results})

        # Fallback to empty schema construct if feasible
        return schema.model_validate({})
