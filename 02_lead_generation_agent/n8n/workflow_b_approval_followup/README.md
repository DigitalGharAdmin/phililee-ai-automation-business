# Workflow B: human approval and follow-up

**Live manual acceptance complete (operator reported).** Import `approval_followup.sanitized.json` as
`PH03 Lead Agent — Approval Follow-up`.

## Purpose and architecture

Authenticated n8n Form -> Validate Decision -> HTTP GET stored lead -> Sheets
lookup -> Eligibility Guard -> approve/reject routing.

Approved: deterministic template -> Sheets sending marker -> confirm marker ->
Gmail Send -> Sheets sent status -> completion result.

Rejected: Sheets rejected/not_sent -> completion result. Ineligible/invalid cases
return a safe completion status and cannot reach Gmail.

## Form and source of truth

Configure a local HTTP Basic Auth credential in the Form node and restrict it to
authorized reviewers. Required fields are `lead_id` (UUID string) and `decision`
(dropdown: exactly approve/reject). Optional notes are trimmed, at most 1000
characters. Unknown decisions, including yes/no/maybe or uppercase APPROVE, are
rejected. The form does not accept contact fields for use in follow-up.

The export sets both `fieldLabel` and `fieldName` to the exact keys `lead_id`,
`decision`, and `notes`. Version 2 uses the label as the output key; newer form
versions support a separate field name. Keep both names aligned when importing
or editing fields. Keep `lead_id` a required Text Input, not a numeric input.
After importing, open a fresh test form and confirm its output includes the entered
UUID under `lead_id` before proceeding with manual acceptance. A missing key in
an existing live form is not reproduced by the offline template checks; check
the imported node configuration and stale test form before retrying. Keep Basic
Auth enabled and select the local credential. The trigger version remains 2 to
preserve the existing Respond to Webhook flow.

HTTP GET uses `http://127.0.0.1:8000/leads/{lead_id}`, with the validated identifier
URL-encoded. FastAPI/database supplies recipient, name, company, service and
qualification. No recipient, score or AI result supplied in the form is trusted.
An unknown lead causes HTTP failure and stops; no email is sent.

The template uses Form Trigger version 2 with `responseNode` and Respond to Webhook
JSON containing `formSubmittedText`. Confirm this on import; later Form versions
may require a supported Form ending node. Results contain fixed status text, not
lead details or arbitrary reviewer notes.

## Eligibility and send guard

The lookup must find exactly one CRM row for the stored lead ID. Missing/conflicting
CRM rows stop with `crm_missing_or_conflicting`; run Workflow A or reconcile the
sheet manually first. A `sent` status or populated follow_up_sent_at returns
`already_sent`, even if the new decision is reject. `sending` returns
`manual_reconciliation_required`. Neither can be cleared by resubmitting the form.

Warm/hot final qualification is required, using deterministic qualification only
if final_qualification is null/missing. Cold/invalid qualification is ineligible.
The CRM state must be awaiting_approval or not_sent. Approve also requires a valid
single recipient email from FastAPI. The only actions reaching the decision IF
are send/reject; only its approved output reaches Gmail.

## Email and status updates

HOT receives a concise invitation to a discovery call. WARM receives a lower-pressure
offer of information or discussion. Both use a controlled service-name dictionary,
the stored name/company, and a fixed Phililee AI Labs signature. Email type is text;
header content does not include free-form lead input. No AI prose, lead score,
internal priority, risk flag, or CRM status is included. No new OpenAI call is made.

Select Gmail OAuth credentials locally; never hardcode a recipient. `sendTo` is
derived from the fetched lead. Gmail retries 3 times with 2000 ms waits, then stops.

Before Gmail, update the CRM to approved/approve, approved_at, and sending. The next
Code node requires confirmation of the matching lead_id and sending marker.
After successful Gmail completion only, update follow_up_status=sent and set
follow_up_sent_at. If Gmail fails, the row remains sending, not sent. If the final
Sheets update fails after delivery, it also remains sending and requires manual
provider/CRM reconciliation. Rejection sets rejected/reject/not_sent and notes;
it never sends or resets a previously sent/sending record.

This is MVP protection, not a transactional messaging system. Gmail retries can
duplicate an ambiguously successful send; simultaneous approvals can race. Process
one approval at a time and never retry from Gmail blindly. Review the shared
[reliability limits](../README.md) before any live test.

## Setup, failures and manual acceptance

Use the same private sheet/tab and [headers](../google_sheets/crm_columns.md) as
Workflow A. Select Google Sheets OAuth on all lookup/update nodes and confirm
manual column mappings and lead_id matching. RAW cell format is required. HTTP
and Sheets failures stop; no Never Error/continue-on-fail path is enabled. Optional
shared error notifications must use fixed safe summaries, not raw provider errors.

- [ ] Confirm form authentication, dropdown, response mode and all node credentials.
- [ ] Fetch an existing hot lead; approve once; verify one delivered test email and sent timestamp.
- [ ] Repeat for a warm lead and verify lower-pressure template wording.
- [ ] Reject an eligible lead; verify rejected/not_sent and no Gmail execution.
- [ ] Approve a cold lead; verify ineligible and no Gmail execution.
- [ ] Resubmit an already-sent lead, including reject: verify no send or state reset.
- [ ] Submit invalid/missing ID, invalid decision, missing CRM row and conflicting CRM rows: no send.
- [ ] Confirm form-supplied recipient fields cannot alter the fetched recipient.
- [ ] Fail the pre-send Sheets update: Gmail must not run.
- [ ] Fail Gmail: sent status must not be written; reconcile the sending marker manually.
- [ ] Fail the post-send Sheets update: verify sending blocks a new attempt.
- [ ] Confirm notifications omit contact details, message bodies and raw errors.
- [ ] Confirm safe completion statuses render in the browser; record sanitized evidence only.

The checklist includes additional scenarios not all reported as live-tested.
Completed acceptance is recorded below and in the
[sanitized evidence summary](../evidence/BUILD_4_MANUAL_ACCEPTANCE.md).

## Verified live manual acceptance

- Basic Auth remained enabled. Required `lead_id` was emitted correctly; required
  decision remained approve/reject only; notes remained optional.
- Reject: validation, stored-lead fetch, CRM lookup and eligibility succeeded.
  The reject branch sent no Gmail and persisted `rejected` / `reject` / `not_sent`,
  preserved notes and updated `last_action_at`.
- Approve: a fresh HOT lead completed automatically without manual node execution.
  Real Gmail delivery was confirmed. Sheets persisted `approved` / `approve` /
  `sent`, populated `approved_at`, `follow_up_sent_at`, `last_action_at`, and
  preserved notes. Approval Result returned `result=sent`.
- Reapproval of the sent lead returned `action=stop`, `result=already_sent`;
  no second Gmail was sent and the Sheets row remained unchanged.
- Gmail OAuth required one manual reconnect, after which delivery succeeded.
  Credentials and recipient details are intentionally excluded.

During reject testing, a Sheets schema refresh exposed extra blank fields.
The accepted live Mark Rejected mapping contains only `lead_id`, `approval_status`,
`approval_decision`, `follow_up_status`, `last_action_at`, and `notes`. Remove extra
blank mappings after schema refresh when configuring a new import.
