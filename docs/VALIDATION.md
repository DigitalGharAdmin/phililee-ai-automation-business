# Repository validation

Run from the repository root in a fresh PowerShell terminal with project dependencies
installed. Close the terminal afterward to discard test-only environment overrides.
These checks use synthetic credentials and isolated SQLite, with no live integrations.

## Customer Support

Use Python 3.13 and this project's requirements-dev.txt. Process values override .env.

```powershell
$env:OPENAI_API_KEY = 'test-key'
$env:APP_ENV = 'testing'
$env:DATABASE_URL = 'sqlite+pysqlite:///:memory:'
$env:RUN_LOCAL_POSTGRES_TESTS = '0'
$env:RATE_LIMIT_BACKEND = 'memory'
$env:RATE_LIMIT_REDIS_URL = ''
$env:FIREBASE_PROJECT_ID = 'demo-test-project'
$env:FIREBASE_CHECK_REVOKED = 'false'
$env:TRUSTED_HOSTS = 'testserver,localhost,127.0.0.1'
$env:CORS_ALLOWED_ORIGINS = 'http://localhost:3000,http://localhost:5173'
$env:ENABLE_HSTS = 'false'
$env:ENABLE_API_DOCS = 'true'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location 01_customer_support_agent
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
Pop-Location
```

Tests supply a synthetic service credential. The classifier requires a nonempty key
at import; test-key satisfies this without an OpenAI request. Firebase and Redis are
faked. Expected: 160 collected, 158 passed, two opt-in PostgreSQL tests skipped,
zero failures. Root CI also checks Alembic using a separate disposable SQLite database.
Local PostgreSQL tests are a separate opt-in integration exercise.

## Lead Generation

Use its own .venv and requirements.txt (validated local Python 3.14).

```powershell
$env:OPENAI_API_KEY = ''
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location 02_lead_generation_agent
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
node n8n/tests/validate_workflows.mjs
.\.venv\Scripts\python.exe -B scripts/audit_publication.py
Pop-Location
```

Expected: 119 Python tests plus 31 offline workflow scenarios, all passing. Tests use
fake AI clients. Workflow simulations do not execute n8n or send Gmail.

## n8n Business Automation

Use Node.js (validated with Node 24); no live n8n instance is required.

```powershell
Push-Location 03_n8n_business_automation
node n8n/tests/validate_portfolio.mjs
Pop-Location
git diff --check
git status --short
```

Expected: 243 passing checks. The validator regenerates sanitized support/sales artifacts
deterministically and validates them locally. Review any resulting diff; no live
Google Sheets, Gmail, OpenAI or n8n credentials are needed.
