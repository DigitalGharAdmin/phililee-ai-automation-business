# Phililee AI Labs

**phililee-ai-automation-business** presents three completed portfolio systems for
customer support, lead qualification and business automation, with working
implementation, validation and documented limits for reviewers and prospective clients.

## Portfolio Projects

### 1. AI Customer Support Agent

FastAPI handles conversational order requests for tracking, cancellation, returns
and refunds with validation and persistent state. SQLAlchemy/PostgreSQL, Alembic,
service/customer authentication, security controls, Docker and CI support the backend.
Separate AI/n8n examples demonstrate automated triage.

[Customer Support project](01_customer_support_agent/README.md)

### 2. AI Lead Generation Agent

Lead intake combines schema validation, deterministic scoring, persistence and
deduplication with optional AI qualification. n8n routes leads to Google Sheets,
preserves CRM state and gates Gmail follow-up on human approval. Reliability checks,
offline scenarios and sanitized manual evidence support the demo.

[Lead Generation project](02_lead_generation_agent/README.md)

### 3. n8n Business Automation

Configurable intake, routing, Google Sheets logging, optional AI classification and
email acknowledgement. Duplicate protection and error/reconciliation handling support
client configurations with support and sales demos.

[Business Automation project](03_n8n_business_automation/README.md)

## Technology

Python, FastAPI, Pydantic, SQLAlchemy, SQLite, PostgreSQL, Alembic, OpenAI SDK,
Firebase Authentication, Redis-compatible rate limiting, Docker, GitHub Actions,
n8n, Google Sheets, Gmail and Node.js offline validators.

## Repository Structure

- .github/workflows/ - repository CI
- 01_customer_support_agent/ - API, tests, deployment and automation evidence
- 02_lead_generation_agent/ - API, approval workflows and demo
- 03_n8n_business_automation/ - templates, client configs, generated demos and tests
- docs/ - repository validation guide

## Validation Status

| Project | Collected | Passed | Skipped | Failed |
| --- | ---: | ---: | ---: | ---: |
| Customer Support | 160 | 158 | 2 | 0 |
| Lead Generation | 150 | 150 | 0 | 0 |
| Business Automation | 243 | 243 | 0 | 0 |

Lead Generation comprises 119 Python tests and 31 workflow scenarios. Customer
Support skips two opt-in PostgreSQL integration tests in the offline environment;
these are not passing results. See [validation commands](docs/VALIDATION.md).

## Security / Privacy

Secrets are not committed. Local .env files, runtime databases and private exports
are ignored. Generated public workflow artifacts are sanitized; credentials are
bound externally by the operator. Public examples use synthetic data. Offline
validation does not call OpenAI, send email or mutate live Sheets/n8n systems.

## Current Status

All three systems are completed portfolio builds. Recorded manual acceptance is
distinguished from repeatable offline tests. Production deployment, external account
configuration and operational guarantees require separate review; these demos do
not claim production certification or exactly-once delivery.
