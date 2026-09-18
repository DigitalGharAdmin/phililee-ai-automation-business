# Sanitized demo scenarios

Scope: MASTER BUILD 04, internal Build 5. These are instructions, not new live evidence.
Use a disposable local demo database. No secrets or real recipients are supplied.
For reproducible routes, use a backend started with an explicitly empty process
OPENAI_API_KEY (see runbook). Workflow A requests AI; this setting yields fallback
and keeps final qualification equal to deterministic qualification. With a real
AI key, final routes may differ within reconciliation rules.

API-only POST /leads never writes Sheets or sends Gmail. The CRM/route outcomes
below apply when the same body is submitted through Workflow A. New captures return
201 and created=true; duplicates return 200 and created=false. Workflow A returns
its own Intake Result, not the full API lead. Safe example.com addresses are not
mailboxes for demonstrating delivery. Use offline tests for sending; any later real
send requires a separately authorized controlled recipient, configured privately.

## 1. HOT lead

Purpose: demonstrate hot qualification. POST `/leads?use_ai=true` or submit
the following to Workflow A:

```json
{
  "name": "Demo Buyer",
  "email": "hot@example.com",
  "message": "Please share general information.",
  "source": "form",
  "service_interest": "lead_generation",
  "budget_range": "5000_plus",
  "timeline": "immediate",
  "company_size": "200_plus"
}
```

Expected API: 201, score 85, qualification/final_qualification `hot`,
`ai_status=fallback`. Expected CRM: `pending` / `awaiting_approval`.
Expected n8n: new-row FALSE -> Upsert CRM Lead -> Intake Result. Gmail: no send.

## 2. WARM lead

Purpose: demonstrate warm qualification. POST `/leads?use_ai=true` or submit
the following to Workflow A:

```json
{
  "name": "Demo Buyer",
  "email": "warm@example.com",
  "message": "Please share general information.",
  "source": "form",
  "service_interest": "other",
  "budget_range": "500_1000",
  "timeline": "within_3_months",
  "company_size": "2_10"
}
```

Expected API: 201, score 47, qualification/final_qualification `warm`,
`ai_status=fallback`. Expected CRM: `pending` / `awaiting_approval`.
Expected n8n: new-row FALSE -> Upsert CRM Lead -> Intake Result. Gmail: no send.

## 3. COLD lead

Purpose: demonstrate cold qualification. POST `/leads?use_ai=true` or submit
the following to Workflow A:

```json
{
  "name": "Demo Buyer",
  "email": "cold@example.com",
  "message": "Please share general information.",
  "source": "form"
}
```

Expected API: 201, score 20, qualification/final_qualification `cold`,
`ai_status=fallback`. Expected CRM: `not_required` / `nurture`.
Expected n8n: new-row FALSE -> Upsert CRM Lead -> Intake Result. Gmail: no send.

## 4. Duplicate lead

Purpose: prove reuse and state preservation. Repeat the exact HOT JSON above
(same body is the copy-paste input; keep service unchanged). API: 200,
created=false, original stored fields returned, no extra AI assessment. CRM: same
row and approval/delivery state unchanged. n8n: TRUE -> Intake Result,
crm_reused; no upsert. Gmail: no send. Same address with a different service is
instead a distinct logical lead.

## 5. AI fallback

Purpose: show capture works without OpenAI. With an empty process key, submit:

```json
{"name":"Fallback Demo","email":"fallback@example.com","message":"Please share general information.","source":"form"}
```

API: 201, ai_status=fallback, ai_assessment=null, score 20, final cold.
CRM: not_required/nurture. n8n: FALSE -> Upsert -> Intake Result. Gmail: no send.
Restart without the key override to restore local AI configuration afterward.

## 6. Reject approval

Purpose: reject an eligible unsent HOT/WARM lead. Form-equivalent payload below;
replace the synthetic UUID privately with the ID returned by your demo intake.
Submit through the Basic Auth form, not a new FastAPI endpoint.

```json
{"lead_id":"00000000-0000-4000-8000-000000000001","decision":"reject","notes":"Demo rejection"}
```

API: GET stored ID returns 200; unknown IDs stop at 404. CRM: rejected/reject/
not_sent, notes retained, last_action_at updated. n8n: valid -> lookup -> eligible
-> reject -> Mark Rejected -> Approval Result. Gmail: no send.

## 7. Approve follow-up

Purpose: show approved follow-up for a fresh eligible HOT lead. Form-equivalent input:

```json
{"lead_id":"00000000-0000-4000-8000-000000000001","decision":"approve","notes":"Demo approval"}
```

Use the fresh demo ID. API: GET 200. n8n: valid -> lookup -> eligible -> approve
-> Mark Sending -> confirmation -> Gmail -> Mark Sent -> result=sent.
CRM: approved/approve/sent; approved_at, follow_up_sent_at and last_action_at populated;
notes retained. Gmail: exactly one send in the sequential successful demo, not an
exactly-once guarantee. Use the offline validator or previously recorded acceptance
for this portfolio step; do not send to example.com or execute live during packaging.

## 8. Double-send guard

Purpose: repeat the exact approval JSON from scenario 7 with the same already-sent
ID. API: GET 200. CRM: unchanged. n8n: Eligibility Guard action=stop,
result=already_sent -> Approval Result. Gmail: no second send. Offline fixtures and
operator-reported Build 4 evidence cover this case without new external actions.
