# AI Customer Support Agent

## Overview

A completed Phililee AI Labs portfolio build for handling order support through
structured conversational requests. FastAPI validates requests, applies deterministic
order rules, and persists tracking, cancellation, return and refund state.
Separate OpenAI classification examples demonstrate AI-assisted triage; the support
API executes its business rules without an LLM.

## Capabilities

- Tracking, cancellation, returns and refunds with order-state validation.
- SQLAlchemy persistence, PostgreSQL support, Alembic migrations and local SQLite.
- n8n service authentication and Firebase customer authentication with ownership checks.
- Bounded requests, safe errors/logging, rate limiting and health/readiness checks.
- Non-root Docker runtime, offline tests and repository-root GitHub Actions CI.

## Architecture

Customer or n8n request -> FastAPI validation/authentication -> support rules ?
SQLAlchemy -> database -> structured response. Verified Firebase identities map to
existing internal customers; the API does not auto-provision customers.

## API / Workflow

| Endpoint | Purpose |
| --- | --- |
| POST /support | Service Bearer authentication; customer_name, order_number, message |
| POST /v2/support | Firebase Bearer authentication; owned order_number and message only |
| GET /health | Minimal liveness |
| GET /ready | Database/shared-limiter readiness |

Debug endpoints are development-only and disabled in production. The active backend
is app/api.py. The local alternate app/api_build02_final.py is not part of the
tracked application and must not be launched.

## Setup

Use Python 3.13. From the repository root in PowerShell:

```powershell
cd 01_customer_support_agent
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Privately configure .env using the [configuration reference](docs/CONFIGURATION.md).
Set the SHA-256 service-key digest before startup; keep the raw service key in the
n8n credential store. Process environment variables override .env. Never commit secrets.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.api:app --reload
```

## Running Tests

Use the exact PowerShell commands in the
[repository validation guide](../docs/VALIDATION.md#customer-support).
OPENAI_API_KEY=test-key is a synthetic classifier import prerequisite: the classifier
constructs its SDK client at import. The offline suite makes no real OpenAI request.
This placeholder is not production configuration.

Verified: **160 collected, 158 passed, 2 PostgreSQL integration tests skipped,
0 failed**. Skipped integration tests are not counted as passing.
[Customer Support CI](../.github/workflows/customer-support-ci.yml) runs tests and
Alembic checks using isolated SQLite and no production credentials.

## Reliability / Security

Service and customer authentication remain separate. Customer operations enforce
ownership with scoped queries and row locks for mutations. Production settings
require PostgreSQL and an external shared limiter. Logs and responses avoid
credentials and unnecessary identity data. See [deployment guidance](docs/deployment.md)
for TLS, migration and runtime controls.

## Portfolio Evidence

Completed automation examples and sanitized evidence:

- [Webhook -> AI -> Sheets](docs/mb02_workflow_1/README.md)
- [Gmail -> AI classification -> Sheets](docs/mb02_workflow_2/README.md)
- [Form -> AI -> email](docs/MB02_Workflow_3/README.md)
- [Shared error handler](docs/mb02_workflow_4/README.md)

Manual integration outcomes are recorded evidence; offline tests do not rerun those
services. See the [three-project portfolio](../README.md).

## Limitations

A completed portfolio build is not production service certification. Deployment,
identity provisioning and external credentials require operator setup. SQLite tests
do not establish PostgreSQL concurrency behavior. Local rate limiting is per process;
production needs shared enforcement. Automation retries do not guarantee exactly-once
delivery. Follow the configuration/deployment guides for separately authorized live checks.
