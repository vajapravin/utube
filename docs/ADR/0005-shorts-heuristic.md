# ADR 0005: Multi-Factor Shorts Classification Heuristic

- **Status**: Accepted
- **Date**: 2026-11-03
- **Deciders**: Full-Stack Architecture Team

---

## Context and Problem Statement
In October 2024, YouTube increased the maximum duration of YouTube Shorts from 60 seconds to 3 minutes (180 seconds). A naive duration filter (`duration <= 180s`) would misclassify brief landscape videos (such as music tracks, short news clips, or quick code snippets) as vertical Shorts, degrading the vertical Shorts player UX.

## Decision Drivers
- High precision: Vertical shorts must render cleanly in the 9:16 Shorts viewer.
- Minimal latency and quota overhead (avoid calling heavy APIs or downloading media).
- Robustness across edge cases.

## Considered Options
- **Option 1**: Naive duration check (`duration <= 180s`).
- **Option 2**: Pure keyword check (requiring `#shorts` in title or description).
- **Option 3**: Multi-factor classification pipeline with optional HTTP HEAD probe.

## Decision Outcome
Chosen option: **Option 3: Multi-factor classification pipeline with optional HTTP HEAD probe**.

### Rationale:
Classification pipeline logic:
1. If `duration_s > 180`, it is definitely **not** a short (`is_short = False`).
2. If `duration_s <= 180`:
   - Check title and description for `#shorts`, `#short`, `#ytshorts`. If present, classify as short (`is_short = True`).
   - Inspect thumbnail aspect ratio or video dimensions if provided in API metadata (e.g. `aspect = 'vertical'`).
   - If ambiguous and `SHORTS_STRICT_CHECK=true`, perform an asynchronous `HEAD` request to `https://www.youtube.com/shorts/{youtube_id}`:
     - Real shorts return HTTP `200 OK`.
     - Standard videos redirect (`303 See Other` to `/watch?v={youtube_id}`).
3. LLM's classification in ranking is used solely as a tie-breaker.

## Consequences
- **Positive**: Eliminates landscape videos in the vertical player; minimal quota impact.
- **Negative**: Optional HEAD request adds ~100ms per ambiguous video (executed during background curation in worker).
