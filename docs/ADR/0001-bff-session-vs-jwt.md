# ADR 0001: Backend-for-Frontend (BFF) Server-Side Sessions vs. Client-Side JWTs

- **Status**: Accepted
- **Date**: 2026-11-03
- **Deciders**: Full-Stack Architecture Team

---

## Context and Problem Statement
The application requires authenticated access for personal and invited family users via Google OIDC. We must choose between:
1. Issuing JWT access and refresh tokens directly to the browser client (stored in `localStorage` or memory).
2. Implementing the Backend-for-Frontend (BFF) pattern, where tokens remain on the server and the browser holds an unguessable session cookie.

## Decision Drivers
- Protection against Cross-Site Scripting (XSS) token exfiltration.
- In-flight revocation capability (instant logout and account termination).
- Single-origin deployment through Caddy reverse proxy.
- Low-memory footprint and native Redis integration.

## Considered Options
- **Option 1**: Client-side JWTs in `localStorage`.
- **Option 2**: Server-side sessions in Redis accessed via `__Host-` prefixed `HttpOnly` cookies (BFF Pattern).

## Decision Outcome
Chosen option: **Option 2: Server-side sessions in Redis (BFF Pattern)**.

### Rationale:
- Storing JWTs in `localStorage` exposes credentials to any potential XSS injection.
- By terminating Google OIDC on FastAPI and issuing an opaque 256-bit session token in an `HttpOnly; Secure; SameSite=Lax; Path=/` cookie prefixed with `__Host-`, browser scripts have zero access to session identifiers.
- Redis allows O(1) revocation, sliding window extensions (30-day sliding TTL), and immediate global revocation on user deletion or password rotation.

## Consequences
- **Positive**: Complete defense against client token theft; instant revocation; simplified frontend state.
- **Negative**: Requires Redis lookups on authenticated requests (negligible latency ~0.2ms over Docker network).
