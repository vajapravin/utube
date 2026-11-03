# Operations Runbook: `mytube`

This guide covers setup, environment configuration, credential generation, deployment (local & Synology DS425+ NAS), and operational maintenance.

---

## 1. Environment Configuration (`.env`)

Create your `.env` file from `.env.example`:

```bash
cp .env.example .env
```

| Key | Description | Default / Example | Required |
|---|---|---|---|
| `APP_NAME` | Display name of the application | `mytube` | Yes |
| `APP_ENV` | Environment mode (`development`, `test`, `production`) | `production` | Yes |
| `PUBLIC_BASE_URL` | Public origin served via Cloudflare | `https://utube.vajapravin.me` | Yes |
| `APP_SECRET_KEY` | 64 random bytes base64-encoded for internal signing | *(Generated)* | Yes |
| `WEB_PORT` | Host port for Caddy ingress | `3005` | Yes |
| `API_PORT` | Host port for FastAPI direct dev access | `8005` | Yes |
| `POSTGRES_PORT` | Host port for PostgreSQL | `5436` | Yes |
| `REDIS_PORT` | Host port for Redis | `6381` | Yes |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `*.apps.googleusercontent.com` | Yes |
| `GOOGLE_CLIENT_SECRET`| Google OAuth Client Secret | *(Secret)* | Yes |
| `ALLOWED_EMAILS` | Comma-separated list of permitted emails | `vajapravin23@gmail.com` | Yes |
| `ALLOWED_DOMAINS` | Permitted email domains (optional) | *(Empty)* | No |
| `OPEN_REGISTRATION` | Disable email allow-list | `false` | No |
| `DB_PASSWORD` | PostgreSQL user password | *(Strong Secret)* | Yes |
| `DB_URL` | SQLAlchemy async connection string | `postgresql+asyncpg://mytube:${DB_PASSWORD}@postgres:5432/mytube` | Yes |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` | Yes |
| `VIDEO_SOURCE` | Video provider (`youtube_data_api` or `fake`) | `youtube_data_api` | Yes |
| `YT_API_KEY` | YouTube Data API v3 key | *(API Key)* | Yes (Prod) |
| `YT_DAILY_QUOTA_BUDGET`| Daily units circuit-breaker limit | `9000` | No |
| `LLM_PROVIDER` | LLM curation engine (`gemini`, `ollama`, `fake`) | `gemini` | Yes |
| `LLM_MODEL` | Model identifier | `gemini-2.5-flash` | No |
| `GEMINI_API_KEY` | Google AI Studio Gemini API Key | *(API Key)* | If gemini |
| `OLLAMA_BASE_URL` | Base URL for local Ollama | `http://ollama:11434` | If ollama |
| `DATA_ROOT` | NAS storage mount point | `/volume1/docker/mytube` | Synology |

---

## 2. External Provider Credentials Setup

### 2.1 Google Cloud Platform (OAuth OIDC)
1. Navigate to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project: `mytube-personal`.
3. Configure the **OAuth Consent Screen**:
   - User Type: **External**.
   - Publishing Status: **Testing**.
   - Add your test user email (e.g. `vajapravin23@gmail.com`).
   - Scopes: Select `openid`, `.../auth/userinfo.email`, and `.../auth/userinfo.profile`.
4. Create **Credentials**:
   - Click **Create Credentials** -> **OAuth Client ID**.
   - Application type: **Web Application**.
   - Authorized redirect URIs:
     - Production: `https://utube.vajapravin.me/api/v1/auth/callback`
     - Development: `http://localhost:3005/api/v1/auth/callback`
5. Copy `Client ID` and `Client Secret` into `.env`.

### 2.2 YouTube Data API v3
1. In the same Google Cloud Project, navigate to **APIs & Services** -> **Library**.
2. Search for **YouTube Data API v3** and click **Enable**.
3. Under **Credentials**, click **Create Credentials** -> **API Key**.
4. Restrict the API key:
   - Application restrictions: None (server-side calls from worker).
   - API restrictions: Restrict key to **YouTube Data API v3**.
5. Copy key into `YT_API_KEY` in `.env`.

### 2.3 Google AI Studio (Gemini 2.5 Flash)
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Click **Get API key** and generate a key for your project.
3. Set `GEMINI_API_KEY` in `.env`.

---

## 3. Local Development Quickstart

### 3.1 Prerequisites
- Python 3.12+ with `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 20+ with `pnpm` (`corepack enable`)
- Docker & Docker Compose v2.20+

### 3.2 Starting the Stack
```bash
# 1. Start core services with one command
make up

# 2. View streaming logs
make logs

# 3. Run migrations and seed categories
make migrate
make seed

# 4. Check container health status
docker compose ps
```

---

## 4. Synology DS425+ NAS Deployment

### 4.1 Storage Directory Structure
Create persistent directories on the NAS volume via SSH or DSM File Station:
```bash
mkdir -p /volume1/docker/mytube/postgres
mkdir -p /volume1/docker/mytube/redis
mkdir -p /volume1/docker/mytube/backups
mkdir -p /volume1/docker/mytube/caddy_data
```

### 4.2 Ingress via Existing Host Cloudflare Tunnel
Following the architecture of `chatapp`, the host already runs a Cloudflare Tunnel container or system daemon:
1. Open the [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/).
2. Navigate to **Networks** -> **Tunnels** and select your active tunnel.
3. Add a Public Hostname route:
   - **Subdomain**: `utube`
   - **Domain**: `vajapravin.me`
   - **Service Type**: `HTTP`
   - **URL**: `localhost:3005` (or `<NAS_LAN_IP>:3005`)
   - **Additional Settings**: Enable HTTP/2, No TLS Verify (if internal HTTPS).

### 4.3 Container Manager Project
1. Open **Container Manager** on DSM.
2. Select **Project** -> **Create**.
3. Name: `mytube`, Path: `/volume1/docker/mytube`.
4. Upload `deploy/docker-compose.yml` and your populated `.env`.
5. Check "Start the project after creation" and deploy.

---

## 5. Maintenance, Backup & Disaster Recovery

### 5.1 Database Backup
Create a timestamped compressed `pg_dump`:
```bash
make backup
# Creates: /volume1/docker/mytube/backups/mytube_backup_YYYYMMDD_HHMMSS.sql.gz
```
Backups are automatically retained for 14 days.

### 5.2 Database Restore
Restore a specific backup archive:
```bash
make restore FILE=/volume1/docker/mytube/backups/mytube_backup_20261103_120000.sql.gz
```

### 5.3 Stale YouTube Metadata Purge (Automated)
YouTube API ToS requires that cached data older than 30 days is purged or refreshed.
A scheduled `arq` job executes daily at 03:00 UTC:
```bash
# To trigger purge manually:
docker compose exec worker python -m app.jobs purge_stale_metadata
```
