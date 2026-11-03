# Synology DS425+ NAS Deployment Guide (`deploy/synology/`)

This guide explains how to deploy `mytube` to a Synology DS425+ NAS (or any Intel-based DSM 7.x Synology NAS) running Container Manager, behind an existing Cloudflare Tunnel on `vajapravin.me`.

---

## 1. Storage Directories

Log into DSM via SSH or use **File Station** to create the application directories under `/volume1/docker/mytube`:

```bash
sudo mkdir -p /volume1/docker/mytube/postgres
sudo mkdir -p /volume1/docker/mytube/redis
sudo mkdir -p /volume1/docker/mytube/backups
sudo mkdir -p /volume1/docker/mytube/caddy_data
sudo mkdir -p /volume1/docker/mytube/caddy_config

# Ensure container users (UID 10001 or postgres UID 70) can write to data folders
sudo chown -R 70:70 /volume1/docker/mytube/postgres
sudo chown -R 999:999 /volume1/docker/mytube/redis
```

---

## 2. Cloudflare Tunnel Ingress

In accordance with our architecture (and aligning with `chatapp`), `mytube` routes traffic through the host's existing `cloudflared` tunnel rather than running a redundant embedded container.

1. Open the [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/).
2. Navigate to **Networks** -> **Tunnels** and select your active tunnel.
3. Add a **Public Hostname**:
   - **Subdomain**: `utube`
   - **Domain**: `vajapravin.me`
   - **Type**: `HTTP`
   - **URL**: `localhost:3005` (or your NAS LAN IP e.g. `192.168.1.100:3005`)
   - **HTTP Settings**: Enable `HTTP/2`.

---

## 3. Container Manager Deployment

1. Open **Container Manager** on Synology DSM.
2. Click **Project** in the left sidebar, then click **Create**.
3. Fill out the Project Wizard:
   - **Project Name**: `mytube`
   - **Path**: Select `/volume1/docker/mytube`
   - **Source**: Choose **Upload docker-compose.yml** and upload `deploy/docker-compose.yml`.
4. Place your configured `.env` file inside `/volume1/docker/mytube/.env`.
5. Select **Next**, enable **Start the project after it is created**, and click **Done**.

---

## 4. Verification

After startup, verify health status in Container Manager:
- `mytube-postgres`: `Healthy` (port 5436)
- `mytube-redis`: `Healthy` (port 6381)
- `mytube-api`: `Healthy`
- `mytube-worker`: `Healthy`
- `mytube-web`: `Healthy` (port 3005)
- `mytube-migrate`: `Exited (0)`

Test via curl from the NAS terminal:
```bash
curl -f http://localhost:3005/api/v1/healthz
```
And access publicly via:
```
https://utube.vajapravin.me
```
