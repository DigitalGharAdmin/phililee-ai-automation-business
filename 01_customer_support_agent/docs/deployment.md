# Production deployment

## Recommended architecture

Use managed container hosting connected to managed PostgreSQL and managed
Redis-compatible storage. This keeps TLS, secrets, logs, health checks, backups,
and GitHub deployments beginner-manageable while preserving a portable container.
Managed application hosting is also simple but less portable; a VPS adds patching,
TLS, database, backup, and monitoring work without helping this portfolio service.

Local start: `.\.venv\Scripts\python.exe -m uvicorn app.api:app --reload`

Production start: `uvicorn app.api:app --host 0.0.0.0 --port $PORT --workers $WEB_CONCURRENCY --no-server-header`

The container defaults to one worker. Scale workers only after checking PostgreSQL
pool totals and confirming the shared Redis limiter. Never use `--reload` in production.

## Configuration contract

Required production names: `APP_ENV`, `DATABASE_URL`,
`N8N_SERVICE_KEY_SHA256`, `FIREBASE_PROJECT_ID`, `CORS_ALLOWED_ORIGINS`,
`TRUSTED_HOSTS`, `RATE_LIMIT_BACKEND`, and `RATE_LIMIT_REDIS_URL`.
Firebase Admin also needs workload identity/Application Default Credentials, or a
secure `GOOGLE_APPLICATION_CREDENTIALS` file mount.

Optional names: `FIREBASE_CHECK_REVOKED`, `MAX_REQUEST_BODY_BYTES`,
`RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`, `ENABLE_API_DOCS`,
`ENABLE_HSTS`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`,
`DB_POOL_TIMEOUT_SECONDS`, `DB_POOL_RECYCLE_SECONDS`, `PORT`, and
`WEB_CONCURRENCY`.

Store secrets only in the hosting secret manager. Prefer workload identity for
Firebase. Never commit `.env`, service-account JSON, raw service keys, database
URLs, or tokens. Use a production database connection with TLS as required by the
managed provider. Size each worker pool so total connections remain below the
database limit. Enable automated backups and test restore procedures.

## Deployment checklist

1. Provision managed container hosting, PostgreSQL, and Redis-compatible storage.
2. Configure production secrets and Firebase ADC/workload identity.
3. Set explicit hosting domains in `TRUSTED_HOSTS` and browser origins in
   `CORS_ALLOWED_ORIGINS`; never use wildcards.
4. Configure managed TLS. Trust forwarded headers only from the hosting proxy at
   the ASGI-server/platform boundary. Enable HSTS after HTTPS is verified.
5. Back up the database. Run `python -m alembic current`, then
   `python -m alembic upgrade head`, then `python -m alembic current`. A migration
   failure must stop rollout. Prefer application rollback; never blindly downgrade
   a production schema or invoke `/debug/reset`.
6. Build and deploy the image. Configure `/health` for liveness and `/ready` for
   readiness. Both responses are intentionally minimal.
7. Run `SMOKE_BASE_URL=https://your-domain.example python scripts/smoke_test.py`.
8. Verify HTTPS, HSTS, trusted-host rejection, CORS, request-size limits, Redis
   rate limiting across instances, production docs 404, and `/debug/*` 404.
9. Send a service-authenticated tracking request to HTTPS `/support` using the
   existing three-field n8n body. Keep the raw key only in n8n's credential store.
10. Obtain a Firebase token locally without printing it and send an owned-order
    tracking request to HTTPS `/v2/support`; never persist or share the token.
11. Change only the n8n HTTP Request URL to deployed HTTPS `/support`, then run a
    workflow smoke test. No workflow code or credential regeneration is required.
12. Watch structured stdout logs by request ID. Add hosted error monitoring later
    only if needed, with secret and identity scrubbing enabled.

For a custom domain: configure DNS at the hosting provider, wait for its managed
certificate, then update `TRUSTED_HOSTS` and `CORS_ALLOWED_ORIGINS`. The provider's
default HTTPS domain is suitable for the initial portfolio deployment.
