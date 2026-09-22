# n8n Business Automation

A reusable n8n system for validating business inquiries, routing work, tracking
requests in Google Sheets and sending policy-controlled acknowledgements. Optional
AI assistance, duplicate protection and explicit failure states support consistent
handling across client configurations.

Start with the [client feature summary](docs/CLIENT_FEATURE_SUMMARY.md) or
[case study](docs/PORTFOLIO_CASE_STUDY.md). Review the [evidence index](docs/EVIDENCE_INDEX.md)
and [acceptance matrix](docs/FINAL_ACCEPTANCE_MATRIX.md) for verification details.

## What it automates

- Authenticated intake, normalization and strict request validation.
- Deterministic classification, priority and configurable queue routing for sales,
  support, complaints, billing and general inquiries.
- Google Sheets tracking with a 24-column Requests schema and request_id lookup.
- Optional structured AI suggestions with deterministic fallback. Suggestions do
  not override business rules or authorize outbound actions.
- Client-specific plain-text acknowledgements under explicit policy.
- Reuse of existing requests without resetting state or sending again.
- Safe failure responses and operator reconciliation for uncertain delivery.

Billing and complaints require review; approval resumption is not implemented.
Routing labels identify work queues, not additional inbox integrations.

## Architecture

```text
Webhook -> Normalize -> Validate -> Rules -> Duplicate check
  Invalid / existing / conflict --------------------------> Respond
  New -> Optional AI -> Reconcile rules -> Confirm Sheets log
      -> Email eligibility -> No send / approval pending -> Respond
      -> Confirm sending marker -> Gmail -> Confirm acceptance
          -> Confirm sent state -------------------------> Respond
          -> Clear rejection -> Confirm failed_safe -----> Respond
          -> Uncertain outcome -> Reconciliation --------> Respond
Unhandled execution failure -> assigned Error Handler
  -> allowlisted metadata -> disabled notification / optional alert -> outcome
```

See the [full architecture](docs/ARCHITECTURE.md) for confirmation/error branches
and the [data contract](docs/DATA_CONTRACT.md) for exact fields and statuses.

## Reliability model

AI and Sheets use three total attempts with 2000 ms waits. Gmail does not retry
automatically. Confirmed clear rejection yields failed_safe / not_sent / send_failed.
Ambiguous sends or unconfirmed state persistence yield needs_reconciliation / unknown /
reconciliation_required. Operators investigate; replay never automatically resends.
Existing sent, sending and unknown rows are reuse-only and retain their timestamps.

These protections apply to sequential workflow states. Sheets/Gmail are not
transactional and do not provide exactly-once delivery. See the
[retry and reconciliation guide](docs/BUILD_3_RELIABILITY.md).

## Client customization

Validated client config -> stable generators -> inactive sanitized core/handler
pair -> private credential and Sheet binding in n8n -> authorized acceptance.

Configure identity, routing, default priority, email/AI policy, acknowledgement
content/version and notification policy without editing core logic. Webhook input
cannot override config. Real operator recipients are bound privately; example.com
notification recipients remain blocked.

| Demo client | Route | Defaults | Response version |
| --- | --- | --- | --- |
| support-demo | support -> support_desk | Email/AI/acknowledgements off | ack-v1 |
| sales-demo | sales -> sales_team | Email/AI off; acknowledgement policy on | sales-ack-v1 |

See [configuration fields](docs/CLIENT_CONFIGURATION.md) and
[onboarding](docs/CLIENT_ONBOARDING.md).

## Quick start

Use Node.js 24 (validated locally); scripts use built-ins without package installation.
From this project directory:

```powershell
node scripts/client_config.mjs config/client_config.support-demo.json
node scripts/build_client_workflow.mjs config/client_config.support-demo.json
node scripts/build_client_workflow.mjs config/client_config.sales-demo.json
node n8n/tests/validate_portfolio.mjs --show-demo
```

These commands use fake providers and do not deploy or send anything. Generated
pairs are in `n8n/generated/`. Follow onboarding before import: bind credentials
privately, select Requests on every Sheets node and verify all mappings. Publish
the authorized test handler first, assign/save it in the core, then publish the
core and confirm webhook registration. Begin with a no-send test.

Follow [demo scenarios](demo/DEMO_SCENARIOS.md) and the
[presentation runbook](demo/DEMO_RUNBOOK.md). Synthetic example.com payloads are for
offline demonstration, not live delivery.

## Live acceptance

Operator-reported acceptance passed for:

- [Build 2](n8n/evidence/BUILD_2_MANUAL_ACCEPTANCE.md): valid/invalid intake,
  no-send, duplicate reuse and authorized Gmail delivery.
- [Build 3](n8n/evidence/BUILD_3_LIVE_ACCEPTANCE.md): error handler, AI transport
  failure, Sheets failure, clear/ambiguous sends and replay guards.
- [Build 4](n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md): both client demos, custom
  content, duplicates, disabled notifications and sanitized exports.

Build 5 adds packaging and offline validation only. No new live provider actions
or successful real OpenAI inference are claimed. Historical Build 2 Gmail retries
were superseded by Build 3's no-retry policy. See
[final validation](n8n/evidence/BUILD_5_FINAL_VALIDATION.md) for current totals.

## Repository structure

| Folder | Contents |
| --- | --- |
| config/ | Sanitized example, support and sales configurations |
| scripts/ | Validators and deterministic generators |
| n8n/workflow_core/, n8n/workflow_error_handler/ | Canonical inactive templates |
| n8n/generated/ | Reviewed client-specific core/handler pairs |
| n8n/tests/ | Actual Code-node execution with fake providers and static checks |
| n8n/evidence/ | Sanitized historical acceptance and current validation |
| demo/ | Presentation sequence, scenarios and synthetic payloads |
| docs/ | Architecture, contracts, case study and delivery guides |

## Security and privacy

Secrets, OAuth material, Basic Auth values, real Sheet IDs and production contacts
are excluded from sanitized exports. Credentials belong in n8n. Private configs,
raw exports and .env files are ignored. Error notifications use fixed/allowlisted
metadata; public summaries exclude raw provider errors. Redaction and scans have
limits; deployment access and retention still need review.

## Known limitations

Sheets is demonstration persistence, not an atomic idempotency store. Serialize
intake/operator changes; concurrent writes may race. Reconciliation is manual,
fingerprints are non-cryptographic and approval resumption is deferred. Credentials,
hosting, monitoring and live configuration are deployment duties. No measured ROI,
guaranteed accuracy or production readiness is claimed. Use the
[handoff checklist](docs/CLIENT_HANDOFF_CHECKLIST.md) and
[production readiness checklist](docs/PRODUCTION_READINESS_CHECKLIST.md).

## Portfolio status

MASTER BUILD 05 - n8n Business Automation: COMPLETE.

- Build 1 - Commercial Automation Scope + Architecture: complete
- Build 2 - Core Business Automation Workflow: complete
- Build 3 - Reliability + Error Handling: complete
- Build 4 - Client Customization Layer: complete
- Build 5 - Demo + Portfolio Packaging: complete

Final offline suite: 243 passed, 0 failed. Prior live acceptance remains documented
separately. No subsequent master build has started; no push or live external action
was performed during Build 5. Next: portfolio review and push preparation.
