# Customer Support Agent

The active FastAPI backend is `app/api.py`.

From `C:\Users\User\Documents\AI_Freelance_Business\01_customer_support_agent`, start it with:

```powershell
python -m uvicorn app.api:app --reload
```

`app/api_build02_final.py` is an older, alternate implementation. It is not the active backend and should not be launched.

## Database

Orders are persisted through SQLAlchemy 2.x. Set `DATABASE_URL` in the local environment or `.env`; production is expected to use PostgreSQL with psycopg:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
```

For disposable local development, SQLite is supported:

```text
DATABASE_URL=sqlite+pysqlite:///./customer_support.db
```

Apply production schema migrations before starting the API:

```powershell
python -m alembic upgrade head
```

Create a new migration after an intentional model change with:

```powershell
python -m alembic revision --autogenerate -m "describe change"
```

## Debug endpoints

All `/debug/*` endpoints are intended only for development and testing. They are enabled by default outside production, or can be controlled explicitly:

```text
APP_ENV=development
ENABLE_DEBUG_ENDPOINTS=true
```

Production must disable them:

```text
APP_ENV=production
ENABLE_DEBUG_ENDPOINTS=false
```

When disabled, every `/debug/*` path returns HTTP 404. `POST /debug/reset` deterministically replaces database order state with the three development records when debug endpoints are enabled; it is not a production seeding strategy.

## n8n service authentication

`POST /support` requires an n8n service credential:

```http
Authorization: Bearer <service-key>
```

Only the SHA-256 digest is configured in the backend:

```text
N8N_SERVICE_KEY_SHA256=<64-character SHA-256 digest>
```

Generate a high-entropy key, store the plaintext only in an n8n Header Auth credential, and calculate its digest without putting the key in shell history:

```powershell
python -c "import hashlib,getpass; print(hashlib.sha256(getpass.getpass('Service key: ').encode()).hexdigest())"
```

Place the printed digest in the backend environment. Never place the plaintext service key in source control, logs, workflow JSON, or `.env.example`.

Configuration is loaded once when the application process starts. Process/deployment
environment variables are always authoritative; the project `.env` supplies defaults
only when a variable is absent from the process environment. This policy is the same in
development and production, so a stale value inherited from a parent shell will take
precedence over `.env`. In production, set configuration through the deployment
environment and do not rely on `.env` overriding it.

Restart the backend after changing credentials or configuration. When diagnosing
environment inheritance, start Uvicorn from a clean shell without `--reload` so the
effective process environment is unambiguous. The n8n Header Auth credential remains
`Authorization: Bearer <service-key>`; store the high-entropy raw key only in n8n and
never commit a real key or digest.

## Customer identity schema foundation

Phase 2A adds a `customers` table with stable internal UUIDs and a nullable
`orders.customer_id` foreign key. The demo reset maps DG-1001, DG-2005, and
DG-3001 to deterministic demo-only customer identities. `orders.customer_name`
remains legacy/display snapshot data and still supports the current behavior;
it must not be treated as the future stable authorization identity.

Firebase customer authentication is available at `/v2/support`. The existing n8n
`POST /support` service authentication and three-field request body are unchanged.

Phase 2B represents authenticated callers with a typed principal. The existing
n8n key produces a service principal with only the support-operations permission.
Customer identity resolution and UUID ownership helpers protect `/v2/support`,
but `/support` still uses its existing service authentication and legacy name check.

## Firebase customer authentication foundation

Firebase Authentication is the selected customer identity provider. The backend has
a separate dependency that verifies Firebase ID tokens, resolves the verified Firebase
UID to an existing internal customer, and rejects disabled, pending, or unprovisioned
customers. It protects the Phase 2D customer endpoint; the current
`/support` route remains n8n-service-only.

Set `FIREBASE_PROJECT_ID` for the expected Firebase project. Firebase Admin uses Google
Application Default Credentials; production should use its platform service identity,
while local credentials may be supplied through the standard
`GOOGLE_APPLICATION_CREDENTIALS` mechanism. Never commit service-account JSON, private
keys, or ID tokens. `FIREBASE_CHECK_REVOKED` is optional and defaults to `false`; enable
it deliberately where the additional remote revocation check is required.

## Customer support endpoint (Phase 2D)

`POST /v2/support` requires a Firebase ID token in the Bearer Authorization header.
Its body contains only `order_number` and `message`; extra fields (including
`customer_name`, `customer_id`, UID, or email) are rejected. Example body:

```json
{"order_number":"DG-1001","message":"Where is my order?"}
```

Ownership is enforced by the authenticated internal customer UUID and order number
in one scoped query, with `FOR UPDATE` for mutations. Foreign, unowned, and
nonexistent orders return the identical HTTP 404 body. No customer auto-provisioning
occurs. Phase 2D keeps `orders.customer_id` nullable. `/support` remains n8n
service-only with its existing three-field body and response; neither route falls
back to the other authentication method. Both routes use the same business rules.

Missing/invalid Firebase credentials return 401; inactive or unmapped customers
return 403. Revoked tokens return 401 when `FIREBASE_CHECK_REVOKED=true`.
Malformed order numbers and blank messages return 400; invalid body shapes return
422 without echoing submitted identity fields. Customer responses omit customer_name
and never include the internal customer UUID.

For a manual check, restart the local backend and use your existing PowerShell
token variable (replace the variable name only, never paste its value):

```powershell
$body = @{order_number='DG-1001'; message='Where is my order?'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v2/support' -Headers @{Authorization="Bearer $idToken"} -ContentType 'application/json' -Body $body
```

The separately provisioned Firebase test customer does not own demo orders, so
DG-1001 should return 404. Repeat with DG-9999 (if nonexistent) and confirm the same
404 body. For a 200 tracking check use an order already explicitly assigned to this
customer; do not remap demo orders. Automated tests cover successful owned-order
operations using isolated fixtures. Do not print/share the token or headers.

Run the full suite including local PostgreSQL persistence and lock checks from the
project directory (the opt-in checks create unique test rows and clean them up):

```powershell
$env:RUN_LOCAL_POSTGRES_TESTS='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
Remove-Item Env:RUN_LOCAL_POSTGRES_TESTS
```

## Production security settings

The authentication boundary remains explicit: `/support` accepts only the trusted
service Bearer credential used by n8n, while `/v2/support` accepts only Firebase ID
tokens and authorizes orders through the mapped internal customer UUID. There is no
credential fallback between routes. Never commit `.env`, credentials, database URLs,
or tokens, and never store or log Firebase ID tokens.

Configure `CORS_ALLOWED_ORIGINS` and `TRUSTED_HOSTS` with explicit deployment values.
Production rejects wildcard values. `MAX_REQUEST_BODY_BYTES` bounds support request
bodies. `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` configure the local
defense-in-depth limiter. Set `RATE_LIMIT_BACKEND=external` in production and enforce
the same or stricter shared limit at the load balancer/API gateway; this is required
for consistent limits across multiple workers or instances. Forwarded headers are not
used for identity or rate-limit decisions, so configure proxy trust at the ASGI server
and deployment boundary rather than accepting arbitrary client forwarding headers.

API documentation is enabled locally and disabled by default in production through
`ENABLE_API_DOCS`. Set `ENABLE_HSTS=true` only when every production request is served
over HTTPS, including correct TLS termination. Do not enable it for local HTTP.
Production TLS and redirects should be enforced at the trusted ingress.

PostgreSQL pooling uses `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`,
`DB_POOL_TIMEOUT_SECONDS`, and `DB_POOL_RECYCLE_SECONDS`, with connection liveness
checks enabled. Production startup validation requires PostgreSQL, a Firebase project,
explicit safe security configuration, and an external shared rate-limit declaration.
Normal support responses include restrictive security/cache headers and a validated
or generated `X-Request-ID`; safe request logs contain only method, path, status,
duration, and that request ID.

## Deployment readiness

The supported runtime is Python 3.13. For local development:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:app --reload
```

Production uses the included non-root container and runs Uvicorn without reload.
Managed container hosting with managed PostgreSQL and Redis-compatible storage is
the recommended architecture. `/health` provides minimal liveness and `/ready`
checks PostgreSQL plus the shared limiter without exposing configuration details.

See `docs/deployment.md` for the production configuration contract, migration order,
TLS/proxy policy, Firebase and n8n smoke tests, custom-domain flow, and rollback
guidance. CI validates the test suite and Alembic using isolated SQLite without
production secrets. Public deployment remains a manual action; CI does not deploy.
