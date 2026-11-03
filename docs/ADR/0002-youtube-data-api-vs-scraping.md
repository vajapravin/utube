# ADR 0002: YouTube Data API v3 vs. Web Scraping (`yt-dlp` / Browser Automation)

- **Status**: Accepted
- **Date**: 2026-11-03
- **Deciders**: Full-Stack Architecture Team

---

## Context and Problem Statement
The app needs to search and retrieve YouTube video metadata (titles, descriptions, channel details, duration, thumbnails) and categorize videos. We must determine whether to use the official YouTube Data API v3 or scrapers such as `yt-dlp` or headless Chrome.

## Decision Drivers
- Strict compliance with YouTube Terms of Service and Developer Policies.
- Resource consumption on the 2 GB RAM Synology DS425+ NAS.
- API stability, latency, and maintenance overhead.
- Quota constraints (10,000 units/day default).

## Considered Options
- **Option 1**: Headless browser or `yt-dlp` scraping.
- **Option 2**: Official YouTube Data API v3 with quota tracking and caching.

## Decision Outcome
Chosen option: **Option 2: Official YouTube Data API v3 with quota tracking and caching**.

### Rationale:
- Scraping YouTube violates YouTube Terms of Service and is subject to rapid anti-bot IP blocks and throttling.
- Headless browsers (Puppeteer/Playwright) consume 300–600 MB RAM per instance, violating our ≤ 1.0 GB RAM budget on the NAS.
- Official API v3 provides structured JSON with exact timestamps, ISO 8601 durations (`PT15M33S`), and reliable pagination.
- To handle the 10,000 daily quota limit, we implement deterministic pre-filtering, 6-hour query caching, and a Redis quota circuit-breaker at 9,000 units.

## Consequences
- **Positive**: Complete legal compliance; lightweight HTTP calls; stable contract; minimal RAM overhead.
- **Negative**: Daily quota cap requires careful query budgeting and batching (`videos.list` batches of 50).
