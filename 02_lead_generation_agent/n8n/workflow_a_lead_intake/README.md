# Workflow A: lead intake, routing and CRM logging

**Manual acceptance pending.** Import `lead_intake_routing.sanitized.json` as
`PH03 Lead Agent — Intake Routing`.

## Purpose and architecture

Webhook -> Normalize Input -> HTTP Capture Lead -> Classify Lead -> Sheets lookup
-> Prepare CRM Row -> IF CRM Exists -> reuse existing row OR append/update by
lead_id -> Intake Result -> Respond to Webhook.

Required nodes: Webhook, Code, HTTP Request, Google Sheets, IF, Respond to Webhook.
No Gmail or OpenAI node exists here. The backend performs optional AI assessment.

## Input and API contract

POST a JSON object to the test URL shown by the Webhook node. The node path is
`ph03-lead-intake`; it is a template route, not a secret. Only the request body is
forwarded. String edges are trimmed; unknown fields remain so FastAPI can reject
them. The workflow does not reproduce the backend validator or scoring rubric.

Required: `name`, `email`, `message`, `source`.
Optional: `company`, `service_interest`, `budget_range`, `timeline`, `company_size`.
Exact enums:

- source: website, form, email, referral, linkedin, facebook, instagram, google_ads, other.
- service_interest: ai_customer_support, lead_generation, email_automation,
  n8n_automation, rag_knowledge_bot, reporting_dashboard, custom_ai_automation, other.
- budget_range: unknown, under_500, 500_1000, 1000_3000, 3000_5000, 5000_plus.
- timeline: unknown, immediate, within_1_month, within_3_months, within_6_months, exploring.
- company_size: unknown, solo, 2_10, 11_50, 51_200, 200_plus.

The HTTP node calls `POST http://127.0.0.1:8000/leads?use_ai=true` with JSON content.
Both 201 new and 200 duplicate responses are parsed as `{created, lead}`. Backend
validation failures stop processing; do not expect a CRM row on HTTP 422. A missing
AI key or AI failure still permits backend deterministic fallback.

## Routing and duplicate handling

Code selects `lead.final_qualification ?? lead.qualification`, never an AI action.

| Route | Initial approval_status | Initial follow_up_status | Behavior |
| --- | --- | --- | --- |
| hot | pending | awaiting_approval | Human follow-up required; eligible for Workflow B |
| warm | pending | awaiting_approval | Human follow-up required; eligible for Workflow B |
| cold | not_required | nurture | Log only; no email |

CRM lookup uses the stored `lead.id`, not email or `created`. An existing row is
reused without writing anything, preserving sent/rejected/sending state, notes and
approval timestamps. Thus a retried intake cannot normally reset an approval guard.
Missing rows use Append or Update Row matched on `lead_id`. Multiple matched rows
raise a fixed identity-conflict error. Backend data remains authoritative; reuse
does not refresh manually changed profile fields. New rows are initialized from
the stored lead, including `ai_assessment.summary` when present.

The response contains only `result` (crm_reused/crm_upserted), `lead_id`, `created`,
`route`, `approval_status`, and `follow_up_status`. It contains no contact fields.
Normal repeated submissions reuse a CRM row; concurrency is not atomic and this
is not distributed exactly-once delivery.

## Setup and failure behavior

Follow the [shared setup](../README.md). Use the exact [CRM columns](../google_sheets/crm_columns.md),
the same `Leads` tab, and local Google Sheets OAuth credentials. Replace the sheet
placeholder in both Sheets nodes. Reads must return all matches; enable Always
Output Data only on the lookup to handle an absent row. Writes use RAW formatting.
No credentials are supplied in the template. Localhost reachability depends on
where n8n runs; adjust the backend URL when using containers or remote n8n.

Any HTTP/Sheets failure stops the workflow. No failure creates an outbound email.
Use fixed safe shared error summaries; never forward raw lead/API error content.

## Manual acceptance checklist

- [ ] Import and confirm all node settings, credentials and response mode.
- [ ] Submit fictional input with required fields through the test webhook.
- [ ] Verify hot and warm receive pending/awaiting_approval; cold receives not_required/nurture.
- [ ] Confirm API-derived route and score, and the same lead_id in the CRM.
- [ ] Repeat identical input: created=false and exactly one CRM row in this sequential test.
- [ ] Repeat after sent/rejected/sending status: status and notes remain unchanged.
- [ ] Same email, different service: distinct backend IDs and CRM rows.
- [ ] Invalid enum returns a stopped execution with no CRM write.
- [ ] Controlled backend or Sheets failure stops processing; notification is payload-safe.
- [ ] Duplicate CRM rows cause a controlled conflict, not an arbitrary update.
- [ ] Check that a string beginning with `=` is stored as text, not a formula.
- [ ] Capture sanitized evidence; do not claim concurrent exactly-once guarantees.
