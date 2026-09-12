# AI Lead Generation Agent

Phililee AI Labs' commercial lead qualification foundation for small and medium
businesses receiving sales inquiries from websites, forms, ads, email, and referrals.
Build 1 validates structured prospect information and returns an explainable,
deterministic preliminary score. No external AI API is required.

## Build 1 scope and architecture

`POST /leads/qualify` -> `LeadCreate` validation -> `score_lead()` -> `LeadQualification`.

The implementation contains only a FastAPI entry point, Pydantic contracts, a pure
scoring function, and product metadata settings. Requests are processed in memory.
`recommended_action` is a recommendation; it does not trigger any action.

```text
app/
  api.py       # HTTP endpoints
  models.py    # input, enum, and response contracts
  scoring.py   # deterministic commercial rubric
  settings.py  # title/version; no secret configuration
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
Build 1 requires no environment variables; `.env.example` documents that fact.
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
`message_quality: 15`. All responses include `reasons`.

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

Build 1 does not yet include AI/LLM scoring, persistence, deduplication, n8n
orchestration, CRM/Sheets logging, automated follow-up, or human approval.
It also has no authentication, Firebase, PostgreSQL, or deployment configuration.
It is a local foundation, not a public production service.

The rubric is a preliminary heuristic, not a verified prediction of conversion.
English keywords cannot understand negation, intent context, or other languages;
the length bonus does not establish genuine detail. Self-reported budget and size
are not verified. Commercial fit should be reviewed before a business decision.

## Next build

Build 2 — Lead Capture, Persistence, and Deduplication.

Later builds may add AI qualification, orchestration, routing, approval, and
follow-up integrations. Those capabilities are outside this build.
