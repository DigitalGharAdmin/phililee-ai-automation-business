# MB05 Business Automation — Core Workflow

Import `business_automation_core.sanitized.json` inactive. Implementation and offline
checks are complete. Five live acceptance scenarios passed per the operator;
[the acceptance record](../evidence/BUILD_2_MANUAL_ACCEPTANCE.md) separates observed
results from offline coverage. New imports still need local configuration checks.

## Sequence and contract

POST Webhook Intake -> Normalize Input -> Validate Input -> Valid Request?
Invalid -> Prepare Invalid Result -> Prepare Final Status -> Respond to Webhook.
Valid -> Apply Business Rules -> Find Existing Request -> Inspect Existing Request.
Existing -> duplicate/conflict response. New -> optional AI or unavailable branch
-> Reconcile Classification -> Prepare Business Log -> Log Business Request ->
confirm log -> Prepare Business Response -> Should Send Email?
No send -> final result. Send -> Mark Sending -> confirm -> Gmail -> confirm
Gmail acceptance -> Mark Sent ->
confirm -> final result. External errors go to fixed safe result handlers.

Webhook: POST `mb05-business-intake`, Basic Auth, responseNode. Submit the JSON body
from [the contract](../../docs/DATA_CONTRACT.md). Enums and booleans remain strict;
unknown fields cannot inject config. Output retains exactly ten public fields.
ai_status is internal/CRM only. HTTP codes: rejected 400, conflict 409, dependency
failure 503, approval/reconciliation 202, logged/completed/duplicate 200.

## Setup

1. Confirm installed support for Webhook 2, Code 2, IF 2.2, HTTP Request 4.2,
   Sheets 4.6, Gmail 2.1 and Respond to Webhook 1.4. Offline tests are not native
   n8n execution; review every imported parameter before enabling.
2. No Code-node module allowlist is required. The fingerprint uses pure JavaScript
   FNV-1a over UTF-16 code units with a 64-bit accumulator and fnv1a64-v1 prefix.
   It is non-cryptographic and NOT for security; only deterministic comparison.
3. Select local HTTP Basic Auth on Webhook, Sheets OAuth on every Sheets node,
   and replace `YOUR_GOOGLE_SHEET_ID` locally. Use a private Requests tab with the
   headers below. Recheck mappings after schema refresh; retain RAW write format.
4. Edit validated client config and rebuild using the Build 4 client generator.
   Do not manually edit core logic for normal onboarding. Enable flags and policy
   are strict booleans; webhook input cannot override the embedded configuration.
5. To enable AI, select a local OpenAI credential, choose a Responses structured-
   output model instead of `YOUR_OPENAI_MODEL`, and set ai_enabled=true. Disabled
   or unconfigured AI yields unavailable. Transport/credential failure yields unavailable; invalid model output yields fallback.
6. Select Gmail OAuth only for separately authorized testing. Sender is the connected
   account. email_enabled alone still requires approval; acknowledgement_policy=true
   explicitly permits fixed sales/support/general acknowledgements. Billing and
   complaint always stay pending. This core contains no approval UI or resumption.
7. Keep inactive until local credentials, response modes and connectivity pass manual
   acceptance. Never send a live demo to example.com. Use a private/HTTPS endpoint.

.env.example is a configuration inventory, not an n8n loader. Map model/label/flags
to client config, sheet ID to native selectors, and keys to local credentials only.

## Requests sheet schema

Use one header row and unique request_id values. Initial append/update mappings:

```text
request_id,payload_fingerprint,received_at,created_at,updated_at,customer_name,email,company,request_type,source,classification,priority,route,action,status,ai_status,result_summary,requires_response,email_status,last_action_at,notes,approval_status,response_version,sent_at
```

No original message, raw AI response or AI summary is stored. ai_status is success,
fallback or unavailable; response_version is ack-v1; approval_status is pending,
policy_allowed or not_required. Later updates change only delivery state, summary,
action and timestamps matched by request_id; notes/profile fields are not blanked.
Do not add extra empty mappings after refresh. Restrict contact-data access/retention.

## AI, send gates and duplicate behavior

AI uses Responses strict structured output, store=false, a 500-output-token cap and
15-second timeout per attempt. Only request_type and redacted message are sent.
Known name/email/company/ID values and obvious email/number/UUID patterns are removed;
this is best-effort redaction, not complete anonymization. Never put secrets in text.
Schema-valid suggestions are discarded after setting ai_status. Deterministic
classification, priority and route always win. Refusal/incomplete/malformed output
and provider failures fall back without preventing logging.

The non-cryptographic fingerprint covers all normalized fields except request_id in
sorted key order. It is internal, not anonymization, and collisions are possible.
The live function was not supplied: byte-for-byte compatibility with existing live
fingerprints is unverified. Earlier SHA-256 or different live-algorithm values will
conflict on replay. Verify compatibility privately before replacing a deployed copy;
never rewrite existing rows or reset send state automatically. One matching ID/fingerprint reuses
stored classification/route/email state without AI, writes or Gmail. Changed content,
multiple matches or corrupt state returns conflict. Failed/pending/unknown records
are never automatically resumed by replaying intake.

Email needs validated input, requires_response=true, both switches true, an allowed
category, a confirmed log and confirmed sending marker. Subject/body are fixed
templates with a bounded local business label, not user or AI prose. No-send states
are not_requested, disabled or pending_approval, preserving Build 1 terminology.

## Failures and Build 3 verification

AI/Sheets use maxTries=3 with 2000 ms waits. Build 3 disables Gmail retries,
superseding the historical Build 2 live setting. Missing/error/malformed Gmail
acknowledgements route to unknown and cannot reach Mark Sent. A confirmed Gmail
message ID means API acceptance, not proof of inbox delivery. Dedicated external-node error outputs
handle expected failures; Never Error is disabled. Lookup/log failure prevents mail.
Sheets Always Output Data intentionally permits absent-row handling and explicit
checking of empty write output. Confirmation failure never opens the send gate.

Sending-marker/ambiguous-Gmail/final-update failure returns unknown/needs_reconciliation and
attempts to persist that state. If Mark Unknown also fails, the result remains safe,
but the row may retain sending or its earlier state. Reconcile provider delivery
before retrying. logged=false means persistence was not confirmed; a failed initial
write might still have committed remotely. Unexpected Code/config/runtime errors
stop execution; not every infrastructure failure can produce a structured response.

Lookup/upsert/send is not atomic. Concurrent requests or write retries can overwrite
state or duplicate rows/delivery. Serialize the MVP, including intake versus manual
updates. No exactly-once guarantee exists. Execution data saving is disabled in the
export; check deployment-wide retention, and never share raw provider diagnostics.

Run `node n8n/tests/validate_workflows.mjs` for core and handler failure scenarios
plus Build 1 checks. Build 3 shared safe error handling and reconciliation guidance
have passed offline checks and operator live acceptance A?H. See
[the current reliability policy](../../docs/BUILD_3_RELIABILITY.md).

Sources: [n8n Sheets mapping implementation](https://github.com/n8n-io/n8n/blob/master/packages/nodes-base/nodes/Google/Sheet/v2/actions/sheet/update.operation.ts),
[OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Assign the shared error workflow after import

Import MB05 Business Automation — Error Handler first. In this core workflow open
Settings > Error Workflow and select MB05 Business Automation — Error Handler,
then save locally. No live workflow ID is hard-coded in the sanitized JSON.
Do not select the handler as its own error workflow. Its notification switch is
off by default; configure any recipient and Gmail credentials privately. Handled
AI/Sheets/Gmail recovery outputs do not necessarily trigger workflow-level errors.

Clear recipient rejection takes Classify Send Failure -> Clear Send Failure? ->
Prepare Send Failed -> Mark Send Failed -> Confirm Send Failed -> Boolean
Send Failed Confirmed? -> Restore Send Failed Result -> final status. Confirmed
state is failed_safe/not_sent/send_failed (HTTP 503), with sent_at blank. Failed
persistence or confirmation requires reconciliation. The update changes only the
three state fields and timestamps, matched by request_id. No automatic retry or
resend occurs for sent, sending, unknown or not_sent duplicate rows.

All 24 initial mappings must remain present as `={{ $json.row.FIELD }}`, matching
on request_id. Selecting/restoring a sheet can clear mappings in n8n; recheck them
after any sheet change. The static validator verifies every mapping.

Build 4 supports client-specific queue labels and fixed acknowledgement content.
See [configuration](../../docs/CLIENT_CONFIGURATION.md). Generated pairs use unique
client webhook paths; new rows use configured routing and response_version. Existing
rows retain prior routes and delivery state even after config updates. The generator
preserves every reliability node, edge, retry policy and 24-column mapping.
