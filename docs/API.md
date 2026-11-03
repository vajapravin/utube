# REST API Specification: `mytube` (`/api/v1`)

All endpoints adhere to REST conventions with JSON payloads, RFC 9457 Problem Details error responses, cursor-based pagination, and double-submit CSRF enforcement on state mutations.

---

## 1. Conventions & Standards

- **Base Path**: `/api/v1`
- **Error Format**: RFC 9457 `application/problem+json`
  ```json
  {
    "type": "https://utube.vajapravin.me/errors/not-found",
    "title": "Resource Not Found",
    "status": 404,
    "detail": "Channel with the specified handle does not exist",
    "instance": "/api/v1/channels/by-handle/unknown"
  }
  ```
- **Pagination**: Cursor-based (`?cursor=<opaque_str>&limit=24`).
  ```json
  {
    "items": [...],
    "next_cursor": "eyJpZCI6...==",
    "has_more": true
  }
  ```
- **Caching**: `ETag` and `If-None-Match` supported on idempotent collection queries.
- **Idempotency**: `Idempotency-Key: <uuid>` supported on resource creation endpoints.

---

## 2. API Endpoint Directory

### 2.1 Authentication & Profile (`/auth`, `/me`)
| Method | Path | Summary | Auth Required | Rate Limit |
|---|---|---|---|---|
| `GET` | `/auth/login` | Initiates Google OIDC flow (302 redirect with PKCE) | No | 20 / min |
| `GET` | `/auth/callback` | Validates Google OIDC callback; sets session cookie | No | 20 / min |
| `POST` | `/auth/logout` | Terminates active Redis session & clears cookies | Yes | 120 / min |
| `POST` | `/auth/logout-all` | Revokes all active sessions for current user | Yes | 20 / min |
| `GET` | `/me` | Retrieves authenticated user profile & preferences | Yes | 120 / min |
| `PATCH`| `/me` | Updates user settings (theme, autoplay, history) | Yes | 120 / min |
| `DELETE`| `/me` | Account erasure (requires `{ "confirm_email": "..." }`) | Yes | 5 / hour |

### 2.2 Onboarding & Categories (`/categories`, `/me/interests`)
| Method | Path | Summary | Auth Required | Rate Limit |
|---|---|---|---|---|
| `GET` | `/categories` | Lists available interest categories catalogue | No | 120 / min |
| `GET` | `/me/interests` | Retrieves categories selected by current user | Yes | 120 / min |
| `PUT` | `/me/interests` | Replaces user interests (enforces 3–10 categories) | Yes | 30 / min |

### 2.3 Feeds & Video Content (`/feed`, `/videos`)
| Method | Path | Summary | Auth Required | Rate Limit |
|---|---|---|---|---|
| `GET` | `/feed/home` | Returns "For you" grid, Continue Watching & category shelves | Yes | 120 / min |
| `GET` | `/feed/categories/{slug}` | Paginated category video grid | Yes | 120 / min |
| `GET` | `/feed/shorts` | Infinite-scroll shorts feed | Yes | 120 / min |
| `GET` | `/videos/{youtube_id}` | Cached video detail (fetches and caches on miss) | Yes | 120 / min |
| `GET` | `/videos/{youtube_id}/up-next` | Contextual recommendations (playlist/channel/category) | Yes | 120 / min |
| `PUT` | `/videos/{youtube_id}/like` | Adds video to user's likes (idempotent) | Yes | 120 / min |
| `DELETE`| `/videos/{youtube_id}/like` | Removes video from user's likes (idempotent) | Yes | 120 / min |
| `PUT` | `/videos/{youtube_id}/hide` | Marks video as "Not interested" for current user | Yes | 120 / min |
| `PUT` | `/videos/{youtube_id}/progress` | Updates playback progress ({ progress_s, duration_s }) | Yes | 240 / min |
| `GET` | `/me/likes` | Paginated list of all videos liked by current user | Yes | 120 / min |
| `GET` | `/videos/{youtube_id}/saved-in` | Returns list of user's playlists containing this video | Yes | 120 / min |

### 2.4 AI-Curated Channels (`/channels`)
| Method | Path | Summary | Auth Required | Rate Limit |
|---|---|---|---|---|
| `POST` | `/channels` | Creates a new AI channel and enqueues curation | Yes | 20 / day |
| `GET` | `/channels` | Lists channels owned by the user (`?owner=me`) | Yes | 120 / min |
| `GET` | `/channels/explore` | Lists public channels across the instance | Yes | 120 / min |
| `POST` | `/channels/preview-plan` | Runs plan generation step without full curation | Yes | 10 / hour |
| `GET` | `/channels/by-handle/{handle}` | Fetches channel header and metadata | Yes | 120 / min |
| `PATCH`| `/channels/{id}` | Updates channel settings or prompt | Yes | 30 / min |
| `DELETE`| `/channels/{id}` | Deletes channel (preserves shared video cache) | Yes | 30 / min |
| `GET` | `/channels/{id}/videos` | Channel videos tab (`?kind=video\|short&sort=`) | Yes | 120 / min |
| `GET` | `/channels/{id}/liked` | Videos in this channel liked by current user | Yes | 120 / min |
| `POST` | `/channels/{id}/refresh` | Triggers manual curation refresh (returns 202) | Yes | 1 / 15 min |
| `GET` | `/channels/{id}/status` | Curation run status polling | Yes | 120 / min |
| `GET` | `/channels/{id}/events` | Server-Sent Events (SSE) stream for curation updates | Yes | 30 / min |
| `POST` | `/channels/{id}/videos` | Manually adds video by YouTube URL or ID | Yes | 60 / min |
| `DELETE`| `/channels/{id}/videos/{youtube_id}`| Removes video and adds to exclusion list | Yes | 60 / min |
| `PATCH`| `/channels/{id}/videos/{youtube_id}`| Pins or unpins video at top of channel | Yes | 60 / min |
| `GET` | `/channels/{id}/runs` | History of last 10 curation runs (owner only) | Yes | 60 / min |

### 2.5 Playlists (`/playlists`)
| Method | Path | Summary | Auth Required | Rate Limit |
|---|---|---|---|---|
| `POST` | `/playlists` | Creates a new playlist | Yes | 60 / min |
| `GET` | `/playlists` | Lists current user's playlists | Yes | 120 / min |
| `GET` | `/playlists/{id}` | Retrieves playlist header and item count | Yes | 120 / min |
| `PATCH`| `/playlists/{id}` | Updates playlist title, description, or visibility | Yes | 60 / min |
| `DELETE`| `/playlists/{id}` | Deletes playlist (Watch later cannot be deleted) | Yes | 30 / min |
| `POST` | `/playlists/{id}/items` | Appends video to playlist | Yes | 120 / min |
| `DELETE`| `/playlists/{id}/items/{item_id}` | Removes video item from playlist | Yes | 120 / min |
| `PATCH`| `/playlists/{id}/items/{item_id}` | Reorders item position via Lexorank string | Yes | 120 / min |

### 2.6 Local Catalog Search (`/search`)
| Method | Path | Summary | Auth Required | Rate Limit |
|---|---|---|---|---|
| `GET` | `/search?q=` | Full-text search across cached videos and channels | Yes | 120 / min |

### 2.7 Operations & Health (`/healthz`, `/readyz`, `/metrics`)
| Method | Path | Summary | Auth Required | Note |
|---|---|---|---|---|
| `GET` | `/healthz` | Process liveness probe | No | Internal & Caddy |
| `GET` | `/readyz` | Readiness probe (verifies Postgres & Redis) | No | Internal & Caddy |
| `GET` | `/metrics` | Prometheus metrics endpoint | No (Internal only) | Blocked by Caddy |
