# Client configuration — format 1

NO SECRET SHOULD BE STORED IN CLIENT CONFIG.

All fields are trusted **build-time** onboarding inputs. No runtime file loading,
webhook override or arbitrary executable policy is supported. Both builders use
the same validated contract in `scripts/client_config.mjs`. Unknown fields at every
level and unsupported versions are rejected; there is no silent migration.
Copy a demo and change data, never the business logic. Generated workflows are
inactive and contain no credentials or real document IDs.

| Field | Type / required | Safe example | Effect and constraints |
| --- | --- | --- | --- |
| config_version | string / yes | `1` | Only version 1 accepted |
| client_id | string / yes | `support-demo` | Lowercase slug, starts with letter, max 50; generated names, filenames and webhook path |
| business_name | string / yes | `Example Support Co` | Max 100, no control characters, HTML or template syntax; acknowledgement label |
| features.email_enabled | boolean / yes | false | Allows consideration of email; never bypasses gates |
| features.acknowledgement_policy | boolean / yes | false | Permits fixed sales/support/general replies only when every send gate passes |
| features.ai_enabled | boolean / yes | false | Optional advisory AI; no authority to send |
| features.operator_notifications_enabled | boolean / yes | false | Handler notification policy; example recipients remain blocked |
| ai.model | string / yes | YOUR_OPENAI_MODEL | Safe model identifier, max 80; placeholder skips AI even if enabled; empty/missing invalid; credential stays external |
| routing.sales | string / yes | sales_queue | Safe queue label, max 64 |
| routing.support | string / yes | support_desk | Same constraints |
| routing.complaint | string / yes | review_queue | Same constraints; does not remove approval requirement |
| routing.billing | string / yes | review_queue | Same constraints; does not remove approval requirement |
| routing.general | string / yes | general_queue | Same constraints; all labels start with lowercase letter and contain lowercase letters/digits/underscore/hyphen; `none` reserved |
| priority.complaint | enum / yes | high | Fixed high; cannot weaken complaint priority |
| priority.high_hint | enum / yes | high | Fixed high |
| priority.general_low_hint | enum / yes | low | Fixed low |
| priority.default | enum / yes | normal | Configurable low/normal/high for remaining cases |
| email.ack_subject | string / yes | We received your inquiry | 1–160 characters, plain text |
| email.ack_body | string / yes | Thank you for contacting {{business_name}}… | 1–2000 characters, plain text; required neutral disclaimer below |
| email.response_version | string / yes | ack-v1 | Max 64, starts alphanumeric, then alphanumeric/dot/underscore/hyphen |
| notifications.operator_recipient | string / yes | operator@example.com | Valid mailbox syntax, max 254; sanitized configs allow example.com only |
| metadata | object / optional | environment: demo | Optional onboarding metadata; not sent to end users or providers |
| metadata.environment | string / required when metadata supplied | demo | Lowercase safe slug, max 32 |

Every row above forbids secrets. Strings reject control characters, suspicious
provider/key/token/password markers and long opaque token-like strings. Checks
report field/category only. Unknown nested fields are rejected. This is a safety
filter, not a guarantee that arbitrary prose contains no confidential information;
review business labels and text before publishing. Configs must contain no real
client contacts or document IDs. Private config filenames are ignored by default.

Acknowledgement text supports only `{{business_name}}`, expanded as literal text
at build time. No customer-message interpolation, HTML or expression evaluation is
supported. The body must contain this exact sentence:

> This acknowledgement does not confirm any purchase, refund or service commitment.

The committed example preserves the previous default wording. Support demo changes
the business identity and support queue with email/AI off. Sales demo changes the
sales queue, subject and response version, enables acknowledgement policy, and
keeps email/AI off. Enabling email in an authorized private config still requires
credentials, requires_response, eligible category, confirmed persistence and all
existing duplicate/reconciliation guards.

Notifications use the configured flag and sanitized recipient in the generated
handler. Every example.com recipient is blocked, even with the flag true. A real
operator recipient must be assigned privately in the imported handler's trusted
notification configuration, with Gmail credentials, before separately authorized
acceptance. Never commit that edited export. This deliberate final binding keeps
real contacts outside the sanitized build pipeline.

Routes are queue labels, not email addresses, URLs or new integrations. New rows
use the configured route; existing valid rows retain their stored route when config
changes. Replays never migrate rows, reset sent_at or resend. Use a separate Sheet
and deployment per client; client_id does not provide tenant isolation. Configuration
updates change newly generated artifacts only and require reimport and acceptance.

Run `node scripts/client_config.mjs config/client_config.support-demo.json` to
validate. Run `node scripts/build_client_workflow.mjs config/client_config.support-demo.json`
to generate the core and handler under `n8n/generated/`. The sales-demo command uses
its corresponding filename. Outputs are deterministic, inactive, and separate from
canonical exports. Rebuilding the same client overwrites its generated pair only.
Canonical regeneration uses the example config through the original builder commands.


Build 4 live acceptance is operator-confirmed; see
[the evidence](../n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md). Generated artifacts remain
inactive and intentionally omit credential bindings, real Sheet IDs, OAuth material,
Basic Auth secrets and production personal emails. Those are bound privately in
n8n. Credential reconnection and saved/published workflow settings affect live
operation without changing the sanitized configuration contract or generated logic.
