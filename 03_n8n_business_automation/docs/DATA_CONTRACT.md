# Version 1 data contracts

Input is a JSON object with no unknown properties. Normalize before validation.
UUID means lowercase 8-4-4-4-12 hexadecimal text. Email accepts one ASCII mailbox
with a dotted domain, no whitespace or display name, maximum 254 characters; this
is deliberately a narrow MVP syntax check, not ownership/deliverability verification.

| Input field | Required/default | Constraint after trimming |
| --- | --- | --- |
| request_id | Required | UUID; supplied by caller and reused on retries |
| customer_name | Required | string, 2-120 characters |
| email | Required | normalized lowercase email |
| company | Optional, null | null or string, 1-200; blank becomes null |
| request_type | Optional, general | sales, support, complaint, billing, general |
| message | Required | string, 10-4000 |
| source | Required | form, webhook, email_import; email_import means authorized adapter, not inbox access |
| priority_hint | Optional, normal | low, normal, high |
| requires_response | Optional, false | boolean, never coerced |

No external_id alias is accepted in v1. Optional null is accepted only for company.

```json
{"request_id":"00000000-0000-4000-8000-000000000001","customer_name":"Demo Customer","email":"customer@example.com","company":null,"request_type":"sales","message":"Please share information about your services.","source":"form","priority_hint":"normal","requires_response":true}
```

Output always contains exactly these ten fields:

| Output field | Type / allowed values |
| --- | --- |
| request_id | UUID or null on invalid ID |
| accepted | boolean, validation accepted rather than delivery success |
| classification | sales, support, complaint, billing, general, or null for invalid/conflicting input |
| priority | low, normal, high, or null |
| route | sales_queue, support_queue, review_queue, general_queue, none |
| action | none, log_only, request_approval, acknowledge, reuse |
| status | rejected, conflict, logged, awaiting_approval, completed, duplicate, failed, failed_safe, needs_reconciliation |
| logged | boolean; true if a durable CRM record exists |
| email_status | not_requested, disabled, pending_approval, sending, sent, failed, not_sent, unknown |
| result_summary | fixed enum: invalid_input, id_conflict, recorded, approval_required, acknowledgement_sent, existing_request, operation_failed, send_failed, reconciliation_required |

Summary follows status in the same listed order. No free text or personal details
are included in output summaries. Valid accepted results require an ID,
classification and priority. rejected/conflict are accepted=false, route=none,
action=none, logged=false, email_status=not_requested. awaiting_approval requires
logged=true, request_approval and pending_approval. completed requires logged=true,
acknowledge and sent. duplicate requires logged=true and reuse. needs_reconciliation
requires logged=true and email_status=unknown. See rules for send gating.

Example with default EMAIL_ENABLED=false:

```json
{"request_id":"00000000-0000-4000-8000-000000000001","accepted":true,"classification":"sales","priority":"normal","route":"sales_queue","action":"log_only","status":"logged","logged":true,"email_status":"disabled","result_summary":"recorded"}
```

[Machine-readable examples](../demo/contracts.json) and the offline validator are
Build 1 artifacts, not an HTTP API or executable n8n workflow. Build 2 should map
rejected/conflict to 400/409, completed/logged/duplicate to 200, awaiting approval or
reconciliation to 202, and failed dependencies to 503; never include upstream text.

Build 3 enum extension: failed_safe requires accepted=true, logged=true,
action=acknowledge, email_status=not_sent, result_summary=send_failed and HTTP 503.
It represents a confirmed persisted pre-send rejection, never ambiguous delivery.
Duplicate not_sent rows remain reuse-only. The ten output keys are unchanged.
