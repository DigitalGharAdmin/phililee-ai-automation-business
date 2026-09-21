# Build 3 manual test plan — reusable procedure

Use a separate authorized test instance, private test sheet and controlled accounts.
This document does not authorize live actions. Retain private execution views outside
Git; record only pass/fail categories. Back up affected test rows and turn off all
three core enable flags afterward. Disable notification sending except in a separately
approved notification test. Never intentionally retry an ambiguous real Gmail send.

Before testing, import both sanitized templates, set native credentials locally,
select the shared handler in core Settings > Error Workflow, and ensure it does not
reference itself. Confirm business Gmail and notification Gmail retries are OFF;
AI/Sheets use 3 attempts/2000 ms. Recheck fingerprint compatibility and serialization.

| Test | Controlled method | Expected evidence |
| --- | --- | --- |
| A. Shared error handler | In an isolated copy, force a generic Stop and Error workflow failure with the handler selected; keep notifications off initially | Error Trigger runs; only fixed/allowlisted metadata leaves normalization; no payload or raw error in prepared message. Later authorized notification yields fixed summary only |
| B. AI fallback | Enable AI only; use unavailable credential or a controlled timeout/malformed response fixture | unavailable for transport errors or fallback for invalid output; deterministic route preserved, logging succeeds if Sheets is healthy, email remains disabled |
| C. Sheets lookup/log | Individually make test lookup and then test logging fail through controlled unavailable permissions/document settings | Retries bounded; failed/logged=false/operation_failed; Gmail never executes; inspect privately whether a write committed remotely |
| D. Gmail before send | In isolated test copy with explicit approval, use an invalid recipient after confirmed sending marker | One attempt; failed_safe/not_sent/send_failed after confirmed persistence; sent_at blank, no actual send |
| E. Gmail ambiguous | Use a local stub or pinned synthetic empty acknowledgement in isolated nodes; do not break a real send connection to manufacture uncertainty | Confirm Gmail Acceptance false; no Mark Sent; unknown path. Test Mark Sent failure separately with an authorized delivery or stub |
| F. Duplicate after sent | Replay an identical synthetic request whose test row is sent | reuse, no writes, no second send |
| G. Duplicate while sending | Seed a test sending row and replay same request | reuse/sending; no Gmail or new writes |
| H. Duplicate unknown/reconciliation | Seed unknown and also needs_reconciliation with a stale no-send marker | reuse/unknown; no resend, no state reset |

Additional checks: empty Sheets update output blocks sending; failed Mark Unknown
still returns a safe reconciliation result; unrelated notes/profile cells remain
unchanged. Check native/proxy generic failure responses never expose raw internals.
Handled failures may not invoke Error Trigger, so inspect both webhook results and
workflow-level failures. A manual handler run may use sample data; validate actual
automatic workflow assignment separately using the controlled failure test.

Record date, test letter, expected/observed status and sanitized outcome only.
No real addresses, message IDs, workflow IDs, credentials or screenshots belong here.
Build 2 live evidence remains separate. Operator Build 3 A?H results are recorded
in [live acceptance](BUILD_3_LIVE_ACCEPTANCE.md); that record describes the actual
controlled methods, which differ from some alternatives in this reusable plan.
