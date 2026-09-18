# Build 2 reconciliation and offline verification

Build 1 contracts remain authoritative. Illustrative Build 2 statuses invalid and
not_sent and a public errors array were not adopted: invalid output remains
rejected/not_requested/invalid_input with exactly ten fields. Fixed validation
error categories are internal only. String booleans and uppercase enums remain
invalid; trimming/defaults do not silently broaden the contract.

AI/Sheets retry 3 attempts with 2000 ms waits. Gmail retains Build 1's no-retry rule
because ambiguous delivery may already have succeeded. Connected external error
outputs allow explicit AI fallback and safe provider-failure responses. This is
minimal core handling, not the deferred shared error workflow. Unexpected code
failures stop; Never Error is not enabled.

Configuration is a trusted Code-node literal plus native credential/document
selectors, not an automatic .env loader. AI suggestions are validated and discarded;
only ai_status persists. Routes are queue labels, not extra inbox integrations.
Authenticated approval/resumption is deferred; pending requests cannot send through
this intake workflow. A local acknowledgement policy permits only fixed replies for
sales/support/general. Billing/complaint cannot bypass approval via that policy.

The initial log may temporarily hold action=acknowledge before delivery. Public
acknowledge results are completed/sent or needs_reconciliation/unknown, not logged.
logged reflects confirmed persistence, not proof that a failed remote write did
nothing. Replay always respects an existing row and never repeats its action.

## Evidence

`node n8n/tests/validate_workflows.mjs` passes 36-node graph checks, 41 workflow
scenarios and 19 Build 1 contract checks. It executes the exported Code nodes and
expressions with in-memory providers, not an n8n runtime. No live import/OAuth
compatibility or provider acceptance is claimed.

Cases include sales/support, invalid ID/email/body/enums/boolean/extra fields,
response=false, disabled email, complaint/billing pending, AI unavailable/success/
refusal/incomplete/malformed/extra fields/error, duplicates and conflicts, duplicate
rows, lookup/log failures, empty writes, ambiguous sends/final updates, unknown-state
write failure and AI payload minimization. Returned provider errors are never echoed.

No live n8n mutation, OpenAI call, Gmail send or Sheets mutation occurred. No shared
error handler or later master build was started. Native import and live acceptance
remain pending. Build 2 implementation/offline scope is complete; next is Build 3.
