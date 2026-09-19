# Build 2 reconciliation and offline verification

Build 1 contracts remain authoritative. Illustrative Build 2 statuses invalid and
not_sent and a public errors array were not adopted: invalid output remains
rejected/not_requested/invalid_input with exactly ten fields. Fixed validation
error categories are internal only. String booleans and uppercase enums remain
invalid; trimming/defaults do not silently broaden the contract.

AI/Sheets and Gmail use 3 attempts with 2000 ms waits as reported in live acceptance.
This closure supersedes Build 1's Gmail no-retry proposal; ambiguous responses can
duplicate delivery inside node retries, despite the sending marker. Connected external error
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
expressions with in-memory providers, not an n8n runtime. These tests alone do not prove live compatibility. Separate operator-reported
manual acceptance is now recorded in the evidence file.

Cases include sales/support, invalid ID/email/body/enums/boolean/extra fields,
response=false, disabled email, complaint/billing pending, AI unavailable/success/
refusal/incomplete/malformed/extra fields/error, duplicates and conflicts, duplicate
rows, lookup/log failures, empty writes, ambiguous sends/final updates, unknown-state
write failure and AI payload minimization. Returned provider errors are never echoed.

No live n8n mutation, OpenAI call, Gmail send or Sheets mutation occurred. No shared
error handler or later master build was started. Five live manual acceptance scenarios have now passed per the operator. Build 2
implementation and manual acceptance are complete. Build 3 has not started.

## Live runtime closure (2026-09-19)

The live Code sandbox rejected the crypto module. The generated node now uses
pure JavaScript FNV-1a over UTF-16 code units, a 64-bit accumulator and fnv1a64-v1
prefix on the same canonical normalized object. This is NOT for security or
anonymization; it is only deterministic identity/comparison and can collide. The
exact live function was not supplied, so existing stored fingerprints require a
private compatibility check before deployment. No records were migrated.

The AI body is now explicitly wrapped as an object expression: ={{ ({ ... }) }}.
The validator checks this wrapper and compiles the expression without injecting
parentheses that could conceal the original regression. Model reference, strict
schema, store=false, token cap, minimized input and instructions are unchanged.
No live AI success is claimed; ai_enabled was false for accepted safe defaults.

Tests reject module loading in Code nodes, check all safe defaults before fixture
overrides, verify fingerprint stability/change sensitivity, and lock the existing
connection graph. Export and generator were updated together. The five live tests
and exact schema are recorded in [manual evidence](../n8n/evidence/BUILD_2_MANUAL_ACCEPTANCE.md).
