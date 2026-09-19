# Build 2 live manual acceptance

Recorded 2026-09-19 from operator-provided results. These tests were performed
before this closure task; no live n8n, OpenAI, Gmail or Sheets action was rerun.
No personal data, real IDs, credentials or private screenshots are included.

| Test | Observed result | Side effects observed by operator |
| --- | --- | --- |
| Valid log-only | accepted=true, sales, normal, sales_queue, log_only, logged, logged=true, email_status=disabled, recorded | Sheets row created; no Gmail |
| Invalid | request_id=null, accepted=false, classification/priority=null, route=none, action=none, rejected, logged=false, not_requested, invalid_input | No Sheets write or Gmail |
| Valid no-send | accepted=true, support, normal, support_queue, log_only, logged, logged=true, not_requested, recorded; requires_response=false | Sheets row created; no Gmail |
| Duplicate | accepted=true, support, normal, support_queue, reuse, duplicate, logged=true, not_requested, existing_request | No duplicate row |
| Send-eligible | accepted=true, sales, high, sales_queue, acknowledge, completed, logged=true, sent, acknowledgement_sent | Row created/finalized; real Gmail delivery confirmed |

Send test used email_enabled=true and acknowledgement_policy=true. The row held
approval_status=policy_allowed, response_version=ack-v1 and populated sent_at.
Afterward the operator restored email_enabled=false, acknowledgement_policy=false,
ai_enabled=false. These are also the committed defaults.

## Runtime fixes and verified configuration

The live Code node rejected the crypto module; a pure JavaScript deterministic
fingerprint resolved it. The repository implements a documented non-cryptographic
comparison function; the exact live function was not provided, so stored-fingerprint
compatibility is not asserted. No security use or collision resistance is claimed.
The AI body syntax was fixed with explicit object-expression parentheses; this does
not constitute a real OpenAI test. Strict schema and minimized payload are preserved.

Webhook: POST mb05-business-intake, Basic Auth, Respond to Webhook. Sheets lookup
and updates match request_id; initial log uses Append or Update Row. The live
Mark Unknown Outcome role maps to the template's Mark Unknown node. AI, Sheets
and Gmail retry settings are maxTries=3, waitBetweenTries=2000. Gmail retries may
duplicate delivery after an ambiguous response; sequential acceptance proves no
exactly-once guarantee. Gmail/OAuth/Basic Auth credential details are excluded.

## Exact Requests header order

```text
request_id
payload_fingerprint
received_at
created_at
updated_at
customer_name
email
company
request_type
source
classification
priority
route
action
status
ai_status
result_summary
requires_response
email_status
last_action_at
notes
approval_status
response_version
sent_at
```

Build 2 live acceptance: COMPLETE, based on the five operator-reported tests.
Build 3 is not started by this task. No new AI or reliability guarantees are claimed.
