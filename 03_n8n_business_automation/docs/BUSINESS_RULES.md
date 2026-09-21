# Deterministic business rules

1. Normalize strings by trimming edges; lowercase the entire email. Preserve message
   case and internal whitespace. Reject non-object input, unknown fields, wrong
   types, invalid email, unsupported enums and out-of-range lengths. UUIDs must
   use canonical lowercase hex. No automatic string-to-boolean conversion.
2. Require caller-generated request_id, customer_name, email, message and source.
   The same logical submission must reuse request_id. Do not deduplicate by email:
   one customer can have multiple legitimate inquiries. Apply documented defaults
   before computing a fingerprint of all normalized business fields except request_id.
3. request_type defines classification. Missing type becomes general. Categories:
   sales, support, complaint, billing, general. No keyword guessing is required.
4. Complaint -> high priority; all other types -> normal. priority_hint=high may
   raise priority; low may lower general only. It cannot lower complaints. Priority
   affects queue order only, never outbound authorization.
5. Routes: sales -> sales_queue; support -> support_queue; complaint or billing ->
   review_queue; general -> general_queue. AI may suggest category/priority and a
   bounded summary for a reviewer, but does not override these Build 2 MVP routes.
6. Log valid new requests before preparing an action. requires_response=false ->
   action=log_only, email_status=not_requested. Disabled email -> action=log_only,
   email_status=disabled. Neither branch sends.
7. With email enabled, billing/complaint always requires authenticated approval.
   Other categories may receive only a fixed acknowledgement under a locally
   approved acknowledgement policy; default policy is approval required. Do not
   perform refunds, payments, promises or arbitrary generated business actions.
8. Approval pending -> action=request_approval, status=awaiting_approval,
   email_status=pending_approval. Reviewer rejection -> log_only/no send. Approved
   response must still satisfy eligibility, logging, sender and duplicate gates.
9. A matching request_id and matching fingerprint returns status=duplicate,
   action=reuse, stored classification/route/email state, and no writes or sends.
   Same ID with different content returns accepted=false, status=conflict, no write
   or send. Preserve original stored approval and delivery states in both cases.
10. AI disabled, timeout, malformed data, refusal or provider failure does not
    reject otherwise valid input. Use the deterministic baseline and fixed fallback
    summary; never expose raw provider errors. Suggested AI output is untrusted.
11. Invalid input returns accepted=false, status=rejected, classification=null,
    priority=null, route=none, action=none, logged=false, email_status=not_requested.
    Echo request_id only if it is a syntactically valid UUID; otherwise null.
12. Logging failure -> accepted=true, status=failed, logged=false, action=none,
    email_status=not_requested. No send. accepted means validated, not completed.
13. Email send transitions: sending marker -> sent confirmation. Known pre-send
    failure with confirmed persistence -> failed_safe/not_sent/send_failed; timeout/ambiguous send or failed post-send persistence ->
    unknown, status=needs_reconciliation. Never blindly retry unknown/sending/sent.
14. Error workflow may notify operators using only fixed error category, stage and
    execution mode. No raw message, payload, email address, headers or provider error text.

Build 3 extends the result enums with failed_safe/not_sent/send_failed and adds a
safe shared notification workflow. Clear failures do not reset sent_at or retry mail.
Approval resumption remains deferred. Gmail automatic retries are disabled; only
a confirmed Gmail success and confirmed final persistence can return completed.
All existing matching rows are reuse-only. A stored needs_reconciliation status
overrides a stale no-send marker to unknown in the returned duplicate result.
See [Build 3 reliability](BUILD_3_RELIABILITY.md) for current policy and limits.

Transport/auth/network AI errors use ai_status=unavailable; malformed model output
uses fallback. Notification-disabled runs reach Notification Outcome as disabled.
Operator live acceptance A?H is complete; see the Build 3 reliability record.
