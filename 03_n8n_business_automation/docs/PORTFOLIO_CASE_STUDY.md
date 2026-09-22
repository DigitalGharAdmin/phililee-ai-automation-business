# Business Automation Case Study

## Problem

Small teams often copy inquiries between forms, inboxes and spreadsheets. Routing
can be inconsistent, acknowledgements repetitive, and retries can trigger duplicate
work. Unclear failure states make recovery harder. This reusable demonstration is
not a named client engagement or a measured revenue study.

## Solution and workflow

Authenticated intake is validated, classified and prioritized using deterministic
rules. Request identity is checked before optional AI assistance and Sheets logging.
A fixed acknowledgement requires policy approval and confirmed persistence. Existing
requests reuse stored state; recovery paths return bounded structured results.
See [architecture](ARCHITECTURE.md).

## Reliability challenges addressed

| Challenge | Implemented response |
| --- | --- |
| Repeated request | Match request_id/fingerprint; reuse without writes/resends |
| Sheets logging failure | failed/logged=false; do not send |
| OpenAI unavailable | Deterministic processing; ai_status=unavailable |
| Clear Gmail rejection | Confirm failed_safe/not_sent/send_failed persistence |
| Ambiguous Gmail outcome | unknown/needs_reconciliation; operator review |
| Resend risk | No Gmail retries; sent/sending/unknown replays never resend |

AI/Sheets retries are bounded. The shared error handler excludes raw customer data
and provider diagnostics from alerts. Cross-service uncertainty still requires
[manual reconciliation](BUILD_3_RELIABILITY.md).

## Client customization

Support demo routes support to support_desk with email off. Sales demo routes sales
to sales_team with its own subject, body and sales-ack-v1 version. Both use the same
core logic. Validated configuration separates onboarding data from code; credentials
and real document IDs remain external.

## Acceptance evidence

Operator-reported Build 2–4 live tests covered intake, logging, authorized Gmail
delivery, recovery, duplicates and both configurations. AI transport failure used
an unreachable local endpoint, not successful real OpenAI inference. Build 5 uses
offline checks only. See the [evidence index](EVIDENCE_INDEX.md) and
[acceptance matrix](FINAL_ACCEPTANCE_MATRIX.md).

## Commercial value

The package reduces repetitive copying and acknowledgement preparation, standardizes
processing, exposes traceable request states and supports reusable onboarding.
Actual savings depend on the client's process and volume; no ROI percentage is
claimed. Delivery includes reviewed configuration, templates and operating guides.

## Technology

n8n, authenticated webhook/API intake, JavaScript Code nodes, Google Sheets, Gmail
and optional OpenAI structured output. Offline checks use Node.js built-ins.

## Security, privacy and limitations

Templates and demo data are sanitized. Client-owned credentials are bound privately
in n8n. Sheets/Gmail are not transactional; retention needs review and reconciliation
is manual. Approval UI, arbitrary CRM integration and production hosting are outside
this package. See [production readiness](PRODUCTION_READINESS_CHECKLIST.md).
