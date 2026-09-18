# Build 4 live manual acceptance

Status: COMPLETE. Recorded: 2026-09-18.
Source: operator-provided live manual acceptance results; this documentation task
neither reran the live workflows nor independently inspected private executions.
No private screenshots, lead values, email addresses, credentials or resource IDs
are included. Repository templates remain sanitized and inactive.

## Workflow A

New HOT returned `crm_upserted`, `created=true`, `route=hot`,
`approval_status=pending`, `follow_up_status=awaiting_approval`.
Existing HOT returned `crm_reused`, `created=false`, preserving CRM state without
a duplicate row. CRM Exists TRUE bypassed upsert; FALSE used upsert.
New COLD returned `route=cold`, `approval_status=not_required`,
`follow_up_status=nurture`.

Sheets persistence was confirmed for `lead_id`, lead metadata, `lead_score`,
`qualification`, `final_qualification`, `final_priority`, `final_recommended_action`,
`ai_status`, `ai_summary`, `approval_status`, `follow_up_status`, `last_action_at`.

## Workflow B

The Basic Auth form emitted required `lead_id`, required approve/reject decision,
and optional notes. Reject passed validation, stored-lead retrieval, CRM lookup
and warm/hot eligibility, followed the reject branch and sent no Gmail. Sheets
stored `approval_status=rejected`, `approval_decision=reject`,
`follow_up_status=not_sent`, preserved notes and updated `last_action_at`.

A fresh HOT approval completed automatically end to end without manual node
execution. Gmail send and real delivery were confirmed. Sheets stored
`approval_status=approved`, `approval_decision=approve`, `follow_up_status=sent`,
populated `approved_at`, `follow_up_sent_at`, `last_action_at` and preserved notes.
Approval Result returned `result=sent`.

Approving the same sent lead again returned `action=stop`, `result=already_sent`.
There was no second Gmail send and no Sheets change.

## Operational corrections and workflow separation

Gmail required one credential reconnect; sending succeeded afterward. No credential
details are recorded. A Sheets schema refresh exposed extra blank reject mappings.
The accepted Mark Rejected mapping was reduced to `lead_id`, `approval_status`,
`approval_decision`, `follow_up_status`, `last_action_at`, `notes`; rejection then
updated the row correctly.

The clean live copies are `PH03 Lead Agent — Intake Routing` and
`PH03 Lead Agent — Approval Follow-up`. The operator manually archived the old
mixed/duplicate copy.

## Scope and next build

These are sequential observed outcomes, not concurrent exactly-once guarantees.
Additional failure-injection and reliability checklist items are not asserted as
live-tested unless listed above. This task modifies documentation only, sends no
email and changes neither live n8n nor Sheets. Build 1–3 behavior is unchanged.

Next: Build 5 — Reliability Tests, Demo Evidence, and Portfolio Packaging.
