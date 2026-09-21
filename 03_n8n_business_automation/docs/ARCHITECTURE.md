# Architecture

```mermaid
flowchart TD
  Input[Authenticated webhook or form] --> Normalize[Trim and normalize]
  Normalize --> Validate[Validate contract]
  Validate -->|Invalid| Result[Safe structured result]
  Validate --> Rules[Deterministic classification and priority]
  Rules --> Duplicate[Request ID lookup]
  Duplicate -->|Duplicate or conflict| Result
  Duplicate -->|New| AI[Optional minimized AI assistance]
  AI --> Route[Deterministic route and action gates]
  Route --> Sheets[Google Sheets tracking]
  Sheets --> Gate[Outbound policy and approval gate]
  Gate -->|Allowed| Gmail[Gmail acknowledgement]
  Gate -->|Disabled or approval required| Result
  Gmail --> Status[Update delivery state]
  Status --> Result
```

Build 2 implements this graph; Build 3 adds a Gmail acknowledgement gate and a
separate privacy-safe error handler. Both templates are inactive with offline checks.
The operator confirmed five live acceptance scenarios; see [Build 2 notes](BUILD_2_NOTES.md).
Duplicate lookup precedes AI to avoid unnecessary external processing. The sequence
does not provide an atomic transaction across Sheets and Gmail.

| Boundary | Required control |
| --- | --- |
| Business input -> n8n | Authenticated intake; bounded strict fields, fixed source/type enums; no input-supplied credentials, recipients other than validated customer email, or arbitrary URLs |
| n8n -> AI provider | Opt-in; send request_type and redacted message only, never structured name/email/company/IDs; bounded structured suggestions; failure preserves baseline |
| n8n -> Sheets | Private per-client sheet; match request_id; RAW cell format; minimal metadata/status; no raw provider responses, original messages or credentials |
| Reviewer -> n8n | Authenticated approval bound to stored request and response version; client input cannot self-approve |
| n8n -> Gmail | Explicit email enablement, durable sending marker and approved eligibility; sender from local credential, fixed acknowledgement template, no AI-authored outbound text |

Use one isolated client deployment/configuration and sheet per client. Do not share
dedup state or credentials across clients. BUSINESS_NAME supplies a template label,
not authorization. GOOGLE_SHEET_ID selects local storage. EMAIL_ENABLED and
AI_ENABLED default false; invalid boolean configuration fails closed. OPENAI_MODEL
must be explicitly selected if AI is enabled; a missing key/model means fallback.
No .env loader or credential provisioning is implemented. Build 2 maps these settings
to a trusted config literal and native credential/document selectors.

Planned CRM columns: request_id, payload_fingerprint, classification, priority, route,
action, status, email_status, customer_name, email, company, source,
requires_response, approval_status, response_version, created_at, updated_at,
sent_at. Fingerprints remain internal and are not anonymization. Retention and
access controls must be agreed with the client; do not retain raw execution data
by default. Keep AI summaries out of shared evidence.

Before any send, verify the stored record and approval state again. Mark sending
before Gmail and sent only afterward. An ambiguous outcome becomes unknown and
requires reconciliation. Build 3 disables Gmail retries and requires a valid
success acknowledgement before Mark Sent, superseding the historical Build 2 live
retry setting. AI/Sheets retain 3 attempts with 2000 ms waits. Sheets/Gmail are not transactional, so serialize the MVP and do
not claim race-safe exactly-once behavior. Production concurrency needs an atomic
claim/idempotency store or an equivalent proven mechanism, outside Build 1.

Workflow-level failures invoke the separately selected Error Trigger workflow.
Handled provider error branches return safe results without necessarily invoking
that trigger. No real error-workflow ID is exported. See
[Build 3 reliability](BUILD_3_RELIABILITY.md) for import setup and trust boundaries.

Build 3 live acceptance A?H is operator-confirmed. Gmail error output now splits
into clear recipient rejection (confirmed failed_safe/not_sent/send_failed) and
ambiguous delivery (needs_reconciliation/unknown, operator review, no resend).
Existing sent/sending/unknown rows retain state and sent_at without writes. The
shared handler false branch reaches Notification Outcome as disabled, with Always
Output Data OFF on its IF. See the reliability document for conservative matching
and the non-atomic Sheets/Gmail limitations.
