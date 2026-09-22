# Build 4 live acceptance

MASTER BUILD 05 — n8n Business Automation, internal Build 4 — Client Customization
Layer. This record documents the operator-supplied manual/live results A–H, reported
for closure on 2026-09-22. These tests were not repeated by the repository agent.
The closure task ran offline only, with no live n8n/provider actions. Build 5 has
not started. Implementation baseline: 520cc0bcb858ea3f0eb629fa1e91221b4d9ef59f.

TEST_A_SUPPORT_IMPORT_CONFIG: PASS

The generated support-demo core and handler imported with their expected names:
MB05 Business Automation - support-demo - Core Workflow and MB05 Business
Automation - support-demo - Error Handler. Config contained client_id=support-demo,
business_name=Example Support Co, all four feature flags false, model placeholder
YOUR_OPENAI_MODEL, support route support_desk, response_version=ack-v1 and the
business name in acknowledgement content. Other routes retained their defaults.
Handler notifications were false with operator@example.com; no secret was observed.

TEST_B_SUPPORT_RUNTIME: PASS

Credentials, the test spreadsheet/Requests tab and error workflow were bound
privately in n8n. Path mb05-support-demo-intake returned accepted=true,
classification=support, priority=normal, route=support_desk, action=log_only,
status=logged, logged=true, email_status=disabled and result_summary=recorded.
A new row retained support/support_desk/logged/disabled. No Gmail or AI ran.
Sheets required credential reconnection/re-authorization: a live credential/session
setup issue, not a generated workflow logic defect. No credential is recorded here.

TEST_C_SALES_IMPORT_CONFIG: PASS

The generated sales-demo core and handler imported with matching sales-demo names.
Config contained client_id=sales-demo, business_name=Example Sales Co,
email_enabled=false, acknowledgement_policy=true, ai_enabled=false and
operator_notifications_enabled=false. Model remained YOUR_OPENAI_MODEL; sales
routed to sales_team, with other routes unchanged. Subject was “We received your
sales inquiry”, body referenced Example Sales Co, and version was sales-ack-v1.
Handler notifications remained false with operator@example.com and safe context.

TEST_D_SALES_RUNTIME: PASS

Private credentials, test spreadsheet/Requests and the matching handler were bound.
The first production request returned 404 until publication/webhook registration
was confirmed. The rerun at mb05-sales-demo-intake returned accepted=true,
classification=sales, priority=normal, route=sales_team, action=log_only,
status=logged, logged=true, email_status=disabled and result_summary=recorded.
The new row retained sales_team/logged/disabled and sales-ack-v1. No Gmail or AI
ran. The initial 404 was a live activation/registration issue, not a logic defect.

TEST_E_SALES_ACK_CONTENT: PASS

The operator temporarily enabled email with acknowledgement policy true and AI
false. The sales result was accepted=true, route=sales_team, action=acknowledge,
status=completed, logged=true, email_status=sent, result_summary=acknowledgement_sent.
The row retained sales-ack-v1 and a populated sent_at. Real delivery was confirmed
by the operator, with the configured sales subject, Example Sales Co body and
non-commitment wording. email_enabled was restored to false after the test.

TEST_F_SALES_DUPLICATE_GUARD: PASS

Replay of Test E's request returned action=reuse, status=duplicate, logged=true,
email_status=sent and result_summary=existing_request. The sent row and sent_at
remained unchanged; no second mail was sent. Client generation preserved the
Build 3 duplicate-send guard.

TEST_G_ERROR_HANDLER_CONFIG: PASS

An intentional failure at Prepare Final Status initially did not invoke the handler
because the error-workflow assignment had not been saved/published. After assigning
the sales-demo handler, saving settings and republishing the core, rerun followed
Error Trigger -> Normalize Error Context -> Prepare Privacy-Safe Error Notification
-> Notify Operator? FALSE -> Notification Disabled -> Notification Outcome.
The result was notification_status=disabled, with no notification Gmail sent.
The temporary intentional error was removed. This was a live setup issue, not
a generated logic failure; operator_notifications_enabled=false was enforced.

TEST_H_GENERATED_SECRET_CHECK: PASS

The operator's manual spot-check of all four generated demo files found no API-key,
bearer/access/refresh token, OAuth secret, private-key or personal-email material.
A private local search for the real Sheet ID also found no matches. The identifier
and search substring are deliberately omitted. This spot-check is supplemented by
the automated publication scan; neither is a claim of exhaustive secret detection.

## Closure verification

Both clients regenerate deterministically without changes to the committed generated
workflows. Offline validation passes 227 scenarios: 130 Build 1–3 regressions and
97 client scenarios, including exact live-accepted defaults and distinct webhook
paths. Handler disabled outcomes, failure paths, duplicate protection, all 24
column mappings and request_id matching remain covered. Secret/privacy scans pass.

Sanitized artifacts intentionally omit credential bindings, real Sheet IDs, OAuth
material, Basic Auth secrets and production personal emails. Live binding remains
private in n8n. New deployments still require local acceptance. Sheets/Gmail are not
transactional; uncertain sends require operator reconciliation, never automatic resend.

BUILD_4_LIVE_ACCEPTANCE: COMPLETE
BUILD_4_STATUS: COMPLETE
NEXT_INTERNAL_BUILD: Build 5 — Demo + Portfolio Packaging (not started)
