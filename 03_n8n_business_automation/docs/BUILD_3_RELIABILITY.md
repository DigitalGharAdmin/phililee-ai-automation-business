# Build 3 — Reliability + Error Handling

Scope: MASTER BUILD 05 internal Build 3 only. Build 2 operator-reported acceptance
remains historical evidence. Build 3 is verified offline; its live test plan is
pending. No external service was invoked and no client customization layer is added.

## Retry policy

| Nodes | Policy | Reason |
| --- | --- | --- |
| AI Classify Request | 3 total attempts, 2000 ms waits; 15-second timeout per attempt | Optional assessment; error output falls back; may incur repeated provider costs |
| All Sheets nodes | 3 total attempts, 2000 ms waits | Reads and repeated fixed-state writes; failures use explicit recovery outputs |
| Send Business Email | One attempt, Retry On Fail disabled | An accepted request with a lost response must not automatically send again |
| Error notification Gmail | One attempt, Retry On Fail disabled | Avoid notification duplicates and recursive failure loops |
| Code/IF/response nodes | No retries | Deterministic transformations; unexpected failures stop |

The Gmail policy deliberately supersedes the Build 2 live configuration. A sending
marker does not protect retries inside a Gmail node. No retry loop exists around
either Gmail node. Gmail Always Output Data permits empty-response detection.
Sheets Always Output Data permits missing-row/empty-confirmation handling. No
Never Error or indiscriminate continue-on-fail setting is enabled.

## External-action failure matrix

| Failure | Public result | Stored state / outbound effect |
| --- | --- | --- |
| Find Existing Request exhausted | failed, logged=false, operation_failed | No write/send; caller cannot assume lookup succeeded |
| Log Business Request exhausted or unconfirmed | failed, logged=false, operation_failed | No send; a remote write might have committed despite failed acknowledgement |
| AI unavailable/disabled | Normal deterministic processing; ai_status=unavailable internally | Logging still possible; no AI authorization |
| AI timeout/auth/network/schema/JSON failure | Normal deterministic processing; ai_status=fallback internally | No raw errors or AI prose returned/stored; existing local policy alone controls send |
| Mark Sending exhausted or unconfirmed | needs_reconciliation, unknown | No Gmail call; attempts to mark unknown conservatively |
| Gmail rejection, timeout, malformed/empty acknowledgement | needs_reconciliation, unknown | No automatic resend; even a clear reported rejection is conservatively reconciled |
| Mark Sent exhausted or missing final confirmation | needs_reconciliation, unknown | Mail may have been accepted; no completed result |
| Mark Unknown exhausted/unconfirmed | needs_reconciliation, unknown | Safe result retained; row may retain sending, sent or an older state |

The ten-field Build 1 result contract remains unchanged. `failed` means a validated
request could not finish; accepted=true is validation acceptance, not completion.
logged=false means no confirmed persistence from this operation, not proof of no
remote side effect. No new failed_safe/not_sent vocabulary is introduced.

## Sending state and duplicate protection

New eligible request -> confirmed log -> sending marker -> confirmed marker ->
one Gmail call -> Confirm Gmail Acceptance -> Mark Sent -> final confirmation.
A nonempty syntactically bounded Gmail message ID on a success output with no error
is required before Mark Sent. The ID is neither returned to the caller nor logged
to Sheets. Acceptance is not proof of inbox delivery. Completed additionally
requires matching request_id, email_status=sent, status=completed and a valid sent_at.

Any uncertain marker/send/finalization takes Prepare Unknown Outcome -> Mark Unknown
-> Restore Unknown Result. email_status=unknown and status=needs_reconciliation mean
the automation will not resend; an operator must inspect actual state first.

An existing matching request is always reuse, never a new write or send:

- logged/no-send or pending: reuse original state; enabling email later does not send it.
- sent: reuse; no second Gmail call.
- sending: reuse; do not resume a stuck run automatically.
- unknown: reuse; manual reconciliation required.
- status=needs_reconciliation with a stale no-send marker: expose email_status=unknown
  in the duplicate response without rewriting the stored row.
- conflicting content/fingerprint, corrupt identity or multiple rows: conflict, no send.

This is duplicate-aware and retry-safe within the documented workflow state model
for sequential requests. It is NOT atomic or exactly-once. Sheets can race during
lookup/upsert, and retries of a write can overwrite concurrently edited cells.
Serialize intake and operator changes for the same request. The non-cryptographic
fingerprint can collide and is not a security or authorization control. Existing
live fingerprint compatibility still requires a private check before replacement.

## Manual reconciliation procedure

1. Pause affected intake executions and operator edits. Preserve the row, request_id,
   fingerprint and notes. Never clear a sending/unknown state simply to bypass a guard.
2. Privately review execution history, the connected account's sent mail and the
   request's timestamps/recipient. Do not paste provider data into alerts or evidence.
3. If delivery/acceptance is confirmed, manually record sent/completed, the verified
   sent_at and corresponding fixed summary; do not execute Gmail again.
4. If positively confirmed not sent, record a terminal no-send state such as
   logged/not_requested with action=log_only and fixed summary=recorded, retaining
   the same identity and an appropriate private audit note. This does NOT schedule
   a resend: this core reuses every existing row. Any desired new delivery requires
   a separate explicit operator authorization and controlled process, not replaying
   from Gmail or inventing a new ID to bypass the guard.
5. If still uncertain, leave unknown/needs_reconciliation. Resume only unrelated work.

No live admin UI, automatic retry queue or approval-resumption workflow is included.

## Shared error workflow and privacy

After import select **MB05 Business Automation — Error Handler** in the core's
**Settings > Error Workflow**. No real workflow ID is serialized. Do not assign the
handler to itself. Native Error Trigger handles workflow-level failures; handled
external error branches may finish successfully and do not automatically trigger it.
Monitor returned failed/reconciliation states separately. The handler neither writes
Sheets nor resumes core execution nor changes the caller's response.

Normalize Error Context starts a fresh allowlisted object: fixed workflow label,
known core node name or Unknown stage, known execution mode or unknown, and fixed
failure category. It never copies error.message, stack, credentials, body, headers,
IDs, links or customer fields. Notification text uses a fixed summary. Optional
notification config is local, disabled by default, and blocks the example recipient.
Notification failure produces only unconfirmed and is not recursively retried.

Error Trigger input and provider diagnostics can still appear privately in n8n's
editor or infrastructure logs. Saved execution data is disabled in both exports;
review instance retention and access control. The known recovery paths produce
safe structured webhook results. Unexpected engine/config/proxy failures may instead
produce n8n's generic HTTP error; confirm production debug/proxy settings do not expose
internals. The handler cannot sanitize infrastructure outside this workflow.

## Verification and limitations

Run `node scripts/build_core.mjs`, `node scripts/build_error_handler.mjs`, then
`node n8n/tests/validate_workflows.mjs`. Validation runs the exported Code nodes and
expressions using in-memory provider substitutes and checks JSON, graph structure,
retry policies, schemas, safe defaults, module restrictions, notification privacy
and repository publication safety. Failure plans exhaust or recover configured
attempts without network calls or real waits. Provider behavior/native import/OAuth
cannot be proven by this harness; follow the separate manual test plan later.

References: [n8n Error Trigger implementation](https://github.com/n8n-io/n8n/blob/master/packages/nodes-base/nodes/ErrorTrigger/ErrorTrigger.node.ts),
[Gmail send response contract](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send).

Offline result: 109 checks passed, 0 failed (19 contract, 81 core, 9 handler).
Both workflow JSON files parse; secret/privacy/tracked-file checks pass.
Build 3 implementation/offline scope: COMPLETE. Live acceptance: PENDING.
