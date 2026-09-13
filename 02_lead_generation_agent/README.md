# AI Lead Generation Agent

Phililee AI Labs' commercial lead qualification foundation for small and medium
businesses receiving sales inquiries from websites, forms, ads, email, and referrals.
Build 2 adds persistent lead capture, stored deterministic qualification, duplicate
prevention, and lead retrieval/listing. The Build 1 rubric remains unchanged.
Build 3 adds optional structured AI assessment and deterministic reconciliation.
An API key is optional; the application starts and provides fallback without it.

## Build 1 scope and architecture

`POST /leads/qualify` -> `LeadCreate` validation -> `score_lead()` -> `LeadQualification`.

The original qualification endpoint uses a pure scoring function and does not
access storage. Capture endpoints now use SQLAlchemy sessions and a SQLite table.
`recommended_action` is a recommendation; it does not trigger any action.

```text
app/
  api.py       # HTTP endpoints
  models.py    # input, enum, and response contracts
  scoring.py   # deterministic commercial rubric
  settings.py  # title/version and DATABASE_URL
  database.py  # engine, session factory, base and session dependency
  db_models.py # Lead ORM table
tests/
  test_api.py
  test_models.py
  test_scoring.py
```

## Input lead schema

Unknown fields are rejected. Optional fields accept omission or JSON `null`.

| Field | Required | Validation |
| --- | --- | --- |
| name | Yes | String, trimmed, 2–120 characters |
| email | Yes | Trimmed, valid email format; domain normalized, local-part case preserved |
| company | No | Trimmed string, at most 200 characters; blank becomes null |
| message | Yes | Trimmed string, 10–5000 characters |
| source | Yes | One of the source values below |
| service_interest | No | One of the service values below |
| budget_range | No | Commercial budget band below |
| timeline | No | Timeline band below |
| company_size | No | Company size band below |

Email format validation does not verify inbox ownership or deliverability. Enum
values are exact lowercase values; invalid values are rejected, not guessed.

Sources: `website`, `form`, `email`, `referral`, `linkedin`, `facebook`, `instagram`,
`google_ads`, `other`.

Services: `ai_customer_support`, `lead_generation`, `email_automation`,
`n8n_automation`, `rag_knowledge_bot`, `reporting_dashboard`,
`custom_ai_automation`, `other`.

## Deterministic scoring rubric

| Category | Values and points | Maximum |
| --- | --- | --- |
| Service interest | Any named commercial service: 20; other: 10; missing: 5 | 20 |
| Budget | 5000_plus: 25; 3000_5000: 22; 1000_3000: 18; 500_1000: 12; under_500: 6; unknown/missing: 5 | 25 |
| Timeline | immediate: 25; within_1_month: 22; within_3_months: 17; within_6_months: 10; exploring: 5; unknown/missing: 5 | 25 |
| Company size | 200_plus: 15; 51_200: 13; 11_50: 11; 2_10: 8; solo: 5; unknown/missing: 5 | 15 |
| Message quality | 3 per distinct intent term, capped at 12; plus 3 if trimmed message length is at least 80 characters | 15 |

Budget bands are USD-equivalent portfolio/demo bands. No currency conversion is
performed. Name, email, company name, and source do not affect the score.

Message matching is case-insensitive and uses whole-word boundaries. Whitespace
is collapsed for matching the phrase `looking for`. The intent terms are:
`price`, `pricing`, `quote`, `cost`, `budget`, `demo`, `consultation`, `implement`,
`implementation`, `automate`, `automation`, `integrate`, `integration`, `need`,
`looking for`, `interested`, `start`, `project`.
Repeated occurrences of the same term earn points once. Different listed forms
such as `implement` and `implementation` count separately.

`lead_score` equals the sum of the five integer `score_breakdown` categories.
The response contract permits 0–100; this rubric's positive defaults mean its
actual minimum is 20 and maximum is 100. Missing optional commercial fields
receive the documented default points.

| Total | Qualification | Priority | Recommended action |
| --- | --- | --- | --- |
| 0–39 | cold | low | nurture |
| 40–69 | warm | medium | review |
| 70–100 | hot | high | contact |

The response also includes five concise reasons explaining the category points.
It does not echo the lead's name, email, or original message.

## Local setup

Use Python 3.14 (the validated local runtime). From the workspace root:

```powershell
cd 02_lead_generation_agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.api:app --reload --host 127.0.0.1
```

If `.venv` already exists, reuse it. No activation is required with these commands.
Use this project's environment rather than the Customer Support Agent environment.
The default is `sqlite:///./lead_generation.db`, relative to the project working
directory. Optionally set `$env:DATABASE_URL` before starting the server.
Settings automatically load this project's `.env` at import, regardless of the
working directory. Explicit process environment variables take precedence, including
explicitly empty values. Optionally copy `.env.example` to `.env` if it does not
already exist, then edit local defaults privately. A missing `.env` is fine.
Restart the server after configuration changes; never commit `.env`.
Stop the development server with Ctrl+C when finished.

Swagger UI: <http://127.0.0.1:8000/docs>.
OpenAPI schema: <http://127.0.0.1:8000/openapi.json>.

## API endpoints

### GET /

Returns HTTP 200 with `status: "ok"`, service title
`Phililee AI Labs — Lead Generation Agent`, and version `1.0.0`.

### POST /leads/qualify

Accepts JSON and returns HTTP 200 with `LeadQualification`. No resource is stored,
so this is a qualification operation rather than a persisted lead creation.

Example request using fictional data:

```json
{
  "name": "Demo Buyer",
  "email": "buyer@example.com",
  "company": "Example Store",
  "message": "We need a quote for an automation project. Please explain the implementation options for our sales team.",
  "source": "website",
  "service_interest": "lead_generation",
  "budget_range": "5000_plus",
  "timeline": "immediate",
  "company_size": "200_plus"
}
```

This request produces score 100, `hot`, `high`, and `contact`, with breakdown
`service_interest: 20`, `budget: 25`, `timeline: 25`, `company_size: 15`, and
`message_quality: 15`. Qualification responses include `reasons`. Capture/retrieval responses contain
stored summary fields instead.

Malformed or invalid requests return HTTP 422 using FastAPI/Pydantic's standard
`detail` list. Validation errors may include rejected input values, so treat error
responses as prospect data. Debug mode is disabled; responses do not include stack
traces. Full field definitions are available in OpenAPI.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover HTTP behavior, validation and normalization, all commercial band
combinations, score sums/ranges, threshold boundaries, message scoring, repeatable
results, and Swagger/OpenAPI generation. They use local fixtures and no external
API calls.

## Current limitations

Build 3 still does not include n8n orchestration, Gmail automation,
Google Sheets/CRM sync, automated follow-up, human approval, production migrations,
or deployment.
It also has no authentication, Firebase, PostgreSQL, or deployment configuration.
It is a local foundation, not a public production service.

The rubric is a preliminary heuristic, not a verified prediction of conversion.
English keywords cannot understand negation, intent context, or other languages;
the length bonus does not establish genuine detail. Self-reported budget and size
are not verified. Commercial fit should be reviewed before a business decision.

## Next build

Build 4 — n8n Routing, Human Approval, Follow-up Email, and CRM/Google Sheets Logging.

Later builds may add orchestration, routing, approval, and
follow-up integrations. Those capabilities are outside this build.

## Build 2 persistence architecture

`POST /leads` -> input validation -> deterministic scoring -> hashed identity lookup
-> SQLAlchemy `Lead` row -> `LeadCaptureResponse`.

`app/database.py` owns the engine, session factory and per-request session cleanup.
Tables are created during FastAPI startup with `Base.metadata.create_all`. Importing
or calling `/leads/qualify` alone does not create database tables. Schema migrations
are deferred to production hardening; `create_all` does not migrate existing tables.

The Lead table stores server-generated UUID text IDs, all normalized input fields,
score, qualification, priority, recommended action, unique indexed `dedup_key`, and
creation/update timestamps. Enums are stored as strings. Timestamps originate in UTC;
SQLite drops timezone information, so API serialization restores UTC explicitly.
Breakdown/reasons are not stored because capture/retrieval needs only the original
qualification summary. Existing stored scores are not recalculated on reads.

## Duplicate identity and behavior

Capture normalizes email by trimming and lowercasing the whole address. Service
interest uses its enum value, or `unspecified` when omitted/null. The key is the
SHA-256 hex digest of `normalized_email + "|" + normalized_service_interest`.
The raw email is not embedded in the key. This hash is an internal lookup mechanism,
not anonymization; guessed identities can still be hashed. It is never returned.

The database's unique index is the final authority. If concurrent inserts race,
the losing request rolls back after `IntegrityError`, fetches the winning row and
returns it as a duplicate. Unrelated database failures return a generic HTTP 500.

Duplicates do not change the existing message, score, other fields, or timestamps.
The same email with a different service is a new lead. Missing service and `other`
are different identities. Build 1 email normalization remains unchanged for the
non-persistent qualification endpoint.

## Capture and retrieval endpoints

| Endpoint | Success | Behavior |
| --- | --- | --- |
| POST /leads | 201 new; 200 duplicate | Same LeadCreate input as qualify; returns `{created, lead}` |
| GET /leads/{lead_id} | 200 | Returns one LeadStored; missing ID returns 404 |
| GET /leads?limit=50 | 200 | Returns an array, newest first; ties ordered by ID |

`LeadStored` includes ID, all input fields, score, qualification, priority,
recommended action, created_at and updated_at. It excludes `dedup_key`, breakdown,
and reasons. The list limit defaults to 50 and accepts integers 1-100. Invalid
input or limits return 422. There is no filtering, search, or offset pagination.
Unexpected database failures return `{"detail":"Database operation failed."}`
with status 500 and no SQL, paths, stack traces, or dedup hashes.

These unauthenticated local endpoints return prospect data; keep the development
server bound to loopback. No email or follow-up is triggered by capture.

## Database tests and local reset

The full pytest command above preserves all Build 1 tests and adds Build 2 tests.
Each persistence test uses a temporary SQLite file and overrides both the database
session dependency and startup engine. Tests never require the developer database.
Coverage includes real unique-constraint violations, simulated stale-read race
recovery, duplicate immutability, retrieval after reconnecting, safe database errors,
and non-persistent qualification.

To reset disposable local development data: stop the server, delete only the local
`lead_generation.db` in this project, and restart the app. If DATABASE_URL points
elsewhere, identify that test database explicitly before deleting anything. Reset
permanently removes locally captured leads. There is no destructive reset endpoint.
Database files and their SQLite journal/WAL sidecars are ignored by Git.

## Build 3: optional AI qualification

Lead Input -> Deterministic Scoring -> AI Structured Assessment -> Reconciliation
-> Final Qualification.

The numerical `deterministic.lead_score` remains the source of truth. AI has no
numeric score field and cannot overwrite it. AI assessment validates intent
strength, business fit, urgency, decision readiness, recommended action, summary
(1-500 characters), up to 8 key signals (1-160 characters each), and up to 8 risk
flags (1-80 characters each). Extra fields, invalid enums and oversized output
are rejected. Structured validation does not prove factual accuracy.

The final state is computed in code, independently of the AI-recommended action:

- Low intent OR poor fit lowers qualification by at most one level.
- High intent AND good/excellent fit AND ready AND no risk flags raises it by at
  most one level.
- Other assessments keep the baseline. Cold cannot jump to hot; hot cannot fall
  to cold. Weak signals take precedence over strong signals.
- Final cold means low/nurture; warm means medium/review; hot means high/contact.
- Failure preserves all deterministic results with `ai_status: fallback` and a
  null assessment. Final reasons use controlled text, not raw provider errors.

`POST /leads/qualify-ai` accepts LeadCreate, returns HTTP 200 LeadAIQualification,
and never persists a lead. Its response includes `deterministic`, `ai_assessment`,
`ai_status`, `final_qualification`, `final_priority`, `final_recommended_action`,
and `final_reasons`. Invalid input still returns 422.

`POST /leads?use_ai=true` opts new captures into assessment. Default `use_ai=false`
preserves deterministic capture and existing fields, adding null AI fields and
final fields equal to the baseline. AI failure still creates a lead (201) using
fallback. Duplicates return the original record (200, created=false), skip AI,
and never update it. Concurrent requests that both pass the initial lookup may
both call AI before one loses the database uniqueness race; this build does not
provide cross-request AI call deduplication.

Stored records retain original deterministic score/labels and add nullable
`ai_status`, a validated `ai_assessment` JSON object, and the three final fields.
JSON preserves the bounded signals/risk lists without extra tables. GET/list
return those fields, never prompts, raw responses/errors, or dedup keys. Older
response objects with missing AI/final fields default to deterministic labels;
this does not migrate old database tables.

## AI configuration, privacy and failures

Set optional `OPENAI_API_KEY` in this project's `.env` or process environment before
starting the app. `OPENAI_MODEL` defaults to `gpt-4.1-mini`; process values override
the automatically loaded `.env`. Keep real
credentials out of shell history and repository files. An empty key causes local
fallback without constructing a client. No credentials are required to run tests.

The OpenAI SDK uses Responses structured output, a 15-second request timeout,
zero retries, a 1200-output-token cap, and `store=False`. Authentication errors,
timeouts, rate limits, service errors, refusal, incomplete output, malformed
output and unexpected SDK exceptions all produce deterministic fallback. No raw
payloads or provider errors are logged by this module. SDK timeout controls network
operations; it is not a strict whole-request wall-clock deadline.

Only company, message, source, service interest, budget, timeline and company size
are sent. Structured name/email fields, IDs, dedup hashes, timestamps and database
metadata are excluded. Free-text company/message fields can themselves contain
personal data; this is field minimization, not automatic redaction. Avoid entering
unnecessary personal information. The prompt treats lead content as untrusted,
forbids invented facts and sensitive-trait inferences, and requests commercial
signals only. Generated prose is advisory, not verified fact. `store=False` does
not imply zero retention under all provider policies.

Implementation references: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
and [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

## Build 3 local database schema change

`create_all` does not add columns to an existing Build 2 database. Startup checks
for missing columns and stops with a generic schema message instead of modifying
or deleting data. Before switching a disposable local database: stop the server,
back up/export anything needed, explicitly delete the intended local
`lead_generation.db`, then restart to create the new schema. Alternatively set
DATABASE_URL to a new local SQLite file and retain the old file for later migration.
No database is automatically reset; production migrations remain a later build.

## Build 3 verification

Run the same full pytest command above. Tests use fake assessment clients and an
in-memory HTTP transport for the installed SDK; they never contact OpenAI. They
cover reconciliation bounds, fallback categories, request privacy, optional capture,
duplicate skipping, stored fields, and non-destructive old-schema rejection.
A global test fixture clears the key and blocks real OpenAI client construction.

No paid smoke test runs automatically. For a deliberately manual check, configure
the key securely, start the local server, and use Swagger POST /leads/qualify-ai
with fictional lead data. This may incur API charges and does not persist a lead.
