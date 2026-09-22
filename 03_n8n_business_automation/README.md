# AI-Powered Business Automation System

MASTER BUILD 05, internal Build 4: Client Customization Layer.
Build 1 defined the contracts. Build 2 provides an inactive sanitized workflow and
offline verification. The operator has now completed the five Build 2 live acceptance
scenarios; see [sanitized evidence](n8n/evidence/BUILD_2_MANUAL_ACCEPTANCE.md).

Small businesses often copy form submissions into spreadsheets, sort inquiries and
write repetitive replies manually. This reusable package will standardize intake,
classification, tracking and controlled responses for service businesses, agencies,
local businesses and online businesses. Client configuration stays separate from rules.

## Commercial scope

The primary MVP processes customer/contact inquiries from a webhook or form,
classifies them, routes work to a team and logs structured records in Google Sheets.
Planned capabilities include optional AI summaries/classification suggestions,
automatic acknowledgements only under explicit policy, internal notifications,
approval-required responses and reporting-ready statuses. Email routing means
routing submitted requests; unrestricted inbox access is not part of the service.

The offer includes client-specific intake/configuration setup, routing rules,
sanitized workflow templates, handoff documentation and acceptance testing. It does
not replace ERP, authorize financial actions or promise unsupported CRM integrations,
exactly-once delivery, zero failures or production readiness.

## MVP and architecture

Intake -> Normalize -> Validate -> deterministic classification -> optional AI
assistance -> rule-based route -> Sheets log -> response/approval gate -> allowed
email -> structured result. Invalid inputs cannot log or send. Duplicates cannot
reset state or resend. AI suggestions cannot authorize actions.

Planned stack: n8n, Google Sheets, Gmail and optional OpenAI. Build 1's validation
uses only Node.js built-ins, with no package installation or network calls.

- [Architecture and trust boundaries](docs/ARCHITECTURE.md)
- [Deterministic rules](docs/BUSINESS_RULES.md)
- [Exact contracts](docs/DATA_CONTRACT.md)
- [Scope, acceptance and Build 2 handoff](docs/BUILD_1_SCOPE.md)
- [n8n implementation plan](n8n/README.md)
- [Synthetic demo fixtures](demo/README.md)

## Reliability and privacy

Email and AI default to disabled. Credentials belong in local n8n credentials or
private runtime configuration, never committed exports. AI receives only minimized
content; free text may still contain private data. Errors use fixed safe summaries.
Sheets is lightweight tracking, not an atomic idempotency store. Concurrent
delivery requires a stronger design before enabling production outbound actions.

## Offline validation

From this project directory run `node scripts/validate.mjs`.
It validates fixtures and negative cases, required documentation, secret/privacy
patterns and Git ignore behavior. It prints only paths/categories on scan failure.
Pattern scanning supplements review and does not prove absence of every secret.

Builds 1-3 are complete. Build 3 live acceptance A-H is operator-confirmed;
[the acceptance record](n8n/evidence/BUILD_3_LIVE_ACCEPTANCE.md) records sanitized outcomes.
Build 4: Client Customization Layer complete, including operator-reported live acceptance.
Next: Build 5 - Demo + Portfolio Packaging (not started).
No later master build is started. Other projects are unchanged.

## Build 2 core workflow

The [inactive core template](n8n/workflow_core/business_automation_core.sanitized.json)
validates authenticated intake, applies deterministic rules, checks request_id,
optionally requests AI assistance, logs to Sheets and gates fixed acknowledgements.
Matching duplicates return stored state without writes or resends. Invalid input
cannot call providers. Email and AI remain disabled by default. Billing/complaint
responses remain pending; no approval-resumption workflow is implemented.

Run `node n8n/tests/validate_workflows.mjs`: 102 core scenarios, 9 handler scenarios
and 19 Build 1 contract checks (130 total). These use actual exported Code nodes and fake providers,
not a live n8n runtime. Run `node scripts/build_core.mjs` and `node scripts/build_error_handler.mjs` to regenerate JSON from
its reviewable source, then rerun validation. No dependency installation is needed.
See [setup/schema/limits](n8n/workflow_core/README.md) and
[contract reconciliations](docs/BUILD_2_NOTES.md).

## Build 3 reliability

Gmail attempts a send at most once per eligible execution and must return a bounded message ID before
Mark Sent. Empty/error acknowledgements and final persistence failures require
manual reconciliation. Existing records never trigger automatic resend. The shared
error handler produces allowlisted metadata only; notifications default off.
See [failure matrix, retry policy and reconciliation](docs/BUILD_3_RELIABILITY.md)
and the [reusable live test plan](n8n/evidence/BUILD_3_MANUAL_TEST_PLAN.md).
This repository synchronization used offline checks only; the operator performed the
live tests separately. Clear recipient rejection now persists failed_safe/not_sent/
send_failed before returning a safe result; uncertain outcomes require reconciliation.

## Build 4 client customization

Build 1: complete. Build 2: complete. Build 3: complete, including operator live
acceptance. Build 4 implementation, offline checks and operator-reported live
acceptance are complete. No Build 5 work is included.

One stable core and error-handler builder consumes validated format-1 configuration.
Business identity, routing, default priority, acknowledgement content/version, email
policy, AI policy and operator notification policy are build-time data. Webhook
input cannot override configuration. Canonical exports stay separate from generated
client pairs; every export remains inactive with no credentials or real Sheet IDs.

From this project directory:

```text
node scripts/client_config.mjs config/client_config.support-demo.json
node scripts/build_client_workflow.mjs config/client_config.support-demo.json
node scripts/build_client_workflow.mjs config/client_config.sales-demo.json
node n8n/tests/validate_clients.mjs
```

The full suite passes 227 scenarios: 130 Build 1-3 checks plus 97 client config,
generation and reliability scenarios. It uses fake providers only. Both demo pairs
are committed for review; private configs and other generated pairs are ignored.
Normal customization requires editing config and rebuilding, not changing core code.
Real credential/document/recipient binding remains a private n8n onboarding step.

See [configuration fields](docs/CLIENT_CONFIGURATION.md),
[onboarding checklist](docs/CLIENT_ONBOARDING.md) and
[completed live acceptance](n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md).

## MASTER BUILD 05 status

- Build 1 - Commercial Automation Scope + Architecture: complete
- Build 2 - Core Business Automation Workflow: complete
- Build 3 - Reliability + Error Handling: complete
- Build 4 - Client Customization Layer: complete
- Build 5 - Demo + Portfolio Packaging: NEXT, not started

The operator completed Build 4 live Tests A-H. This closure task only rebuilt and
validated local artifacts; it performed no live actions. See the acceptance record
for results and the onboarding guide for credential and publication safeguards.
