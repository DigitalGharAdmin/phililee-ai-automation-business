# AI-Powered Business Automation System

MASTER BUILD 05, internal Build 2: Core Business Automation Workflow.
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

Builds 1 and 2: COMPLETE for their documentation/implementation/offline scope.
Live acceptance is operator-confirmed; no live actions were rerun for closure. Next: Build 3 — Reliability + Error Handling.
No later master build is started. Other projects are unchanged.

## Build 2 core workflow

The [inactive core template](n8n/workflow_core/business_automation_core.sanitized.json)
validates authenticated intake, applies deterministic rules, checks request_id,
optionally requests AI assistance, logs to Sheets and gates fixed acknowledgements.
Matching duplicates return stored state without writes or resends. Invalid input
cannot call providers. Email and AI remain disabled by default. Billing/complaint
responses remain pending; no approval-resumption workflow is implemented.

Run `node n8n/tests/validate_workflows.mjs`: 36 nodes, 41 offline workflow scenarios
and 19 Build 1 contract checks. These use actual exported Code nodes and fake providers,
not a live n8n runtime. Run `node scripts/build_core.mjs` to regenerate the JSON from
its reviewable source, then rerun validation. No dependency installation is needed.
See [setup/schema/limits](n8n/workflow_core/README.md) and
[contract reconciliations](docs/BUILD_2_NOTES.md).
