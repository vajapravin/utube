# ADR 0006: External Cloudflare Tunnel Ingress Architecture

- **Status**: Accepted
- **Date**: 2026-11-03
- **Deciders**: Full-Stack Architecture Team

---

## Context and Problem Statement
Deployments on residential CGNAT networks (such as the target Synology DS425+ NAS) lack public IPv4 inbound port forwarding. Ingress is handled via Cloudflare Tunnel. We must decide whether to run an embedded `cloudflared` container inside the `mytube` Compose file or integrate with the pre-existing host tunnel daemon, following `chatapp`'s proven setup.

## Decision Drivers
- Memory and process conservation on the 2 GB NAS.
- Maintenance consistency across self-hosted apps (`chatapp`, `mytube`).
- Multi-host flexibility (running seamlessly on dev laptops and production NAS).

## Considered Options
- **Option 1**: Mandatory embedded `cloudflared` container in `core` profile.
- **Option 2**: Single-origin Caddy binding to dedicated host port (`3005`), integrated with existing host Cloudflare Tunnel, plus an optional standalone `cloudflare` profile for local testing.

## Decision Outcome
Chosen option: **Option 2: Single-origin Caddy binding to dedicated host port (`3005`), integrated with existing host Cloudflare Tunnel**.

### Rationale:
- In `chatapp` (commit `48c73ec4`), the embedded `cloudflared` container was intentionally removed because running multiple tunnel containers on the same NAS creates redundant outbound QUIC connections and wastes memory (~35–64 MB RAM).
- The NAS host already runs a central Cloudflare Zero Trust agent mapped to `*.vajapravin.me`.
- By mapping `utube.vajapravin.me` -> `http://localhost:3005`, Caddy handles ingress, static asset serving, and `/api/*` reverse proxying with zero extra tunnel overhead.
- For isolated environments without a host tunnel daemon, an optional `cloudflare` profile (`docker compose --profile cloudflare up`) is provided.

## Consequences
- **Positive**: Saves ~50 MB RAM; standardizes on single host tunnel; zero redundant daemons.
- **Negative**: Requires one-time DNS/tunnel mapping in Cloudflare Zero Trust Dashboard for `utube.vajapravin.me`.
