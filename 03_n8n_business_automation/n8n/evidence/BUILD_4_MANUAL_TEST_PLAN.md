# Build 4 manual acceptance — planned, not executed

All cases below require separate authorization and an isolated deployment. No live
n8n, OpenAI, Gmail or Sheets action was performed during Build 4 implementation.
Use private controlled accounts; record only sanitized outcomes, never credentials,
real contacts, document/workflow IDs, provider responses or screenshots containing data.

| Case | Planned action | Expected result |
| --- | --- | --- |
| A | Import support-demo core and handler inactive | Valid graph, no embedded credentials; client-specific path and name |
| B | Inspect trusted config and prepared acknowledgement | Example Support Co applied literally |
| C | Submit authorized synthetic support inquiry | support_desk route persisted and returned |
| D | Run support flow with default email=false | No Gmail execution; disabled or not_requested |
| E | Import sales-demo pair separately | Distinct path/name, placeholders and inactive state retained |
| F | Inspect prepared sales acknowledgement | Configured subject/body, neutral disclaimer and sales-ack-v1 |
| G | Separately enable email and bind credentials in test instance | Only valid eligible requests with response requested and confirmed persistence send; policy=false and billing/complaint do not send |
| H | Replay sent/sending/unknown and changed-config rows | Reuse only; no resend/write, stored route/state/sent_at preserved |
| I | Verify handler config with notifications disabled and then flag=true/example recipient | Both remain disabled; optional real-recipient test requires private binding and separate authorization |
| J | Review sanitized export against config and publication checks | No credentials, real contacts/Sheet IDs or private execution data |

Also verify clear rejection -> failed_safe/not_sent/send_failed; uncertain delivery
or failed persistence -> needs_reconciliation/unknown without automatic resend.
Inspect all 24 Sheets mappings after selecting the local sheet. Verify the selected
error workflow and its disabled path ending in Notification Outcome. AI placeholder
skips calls; any optional live AI test needs separate approval and private credentials.
Restore all core flags and notifications to false after testing; retain private
evidence outside Git. These planned cases are not claimed as PASS.
