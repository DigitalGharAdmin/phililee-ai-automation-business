# Google Sheets CRM columns

Create a private spreadsheet with tab `Leads`. Put these exact headers in row 1,
in this order; data begins in row 2. Do not add duplicate headers or merged cells.

| Column | Meaning |
| --- | --- |
| `lead_id` | Stored lead.id; required unique CRM key, never email alone. |
| `created_at` | Backend UTC creation timestamp. |
| `name` | Stored business lead field from FastAPI; optional values become blank. |
| `email` | Stored business lead field from FastAPI; optional values become blank. |
| `company` | Stored business lead field from FastAPI; optional values become blank. |
| `source` | Stored business lead field from FastAPI; optional values become blank. |
| `service_interest` | Stored business lead field from FastAPI; optional values become blank. |
| `budget_range` | Stored business lead field from FastAPI; optional values become blank. |
| `timeline` | Stored business lead field from FastAPI; optional values become blank. |
| `company_size` | Stored business lead field from FastAPI; optional values become blank. |
| `lead_score` | Original deterministic numerical score. |
| `qualification` | Original deterministic label. |
| `final_qualification` | Final label, or qualification if unavailable. |
| `final_priority` | Stored final priority, or deterministic priority. |
| `final_recommended_action` | Stored final action, or deterministic action. |
| `ai_status` | success/fallback or blank when not attempted. |
| `ai_summary` | Validated assessment summary only; no raw AI response. |
| `approval_status` | pending, not_required, approved, rejected. |
| `approval_decision` | Blank initially; approve or reject. |
| `approved_at` | UTC time approval/send preparation was recorded. |
| `follow_up_status` | awaiting_approval, nurture, sending, sent, not_sent. |
| `follow_up_sent_at` | UTC timestamp written only after Gmail success. |
| `last_action_at` | UTC time CRM row creation or approval action was recorded. |
| `notes` | Bounded reviewer notes; necessary context only. |

All write nodes use RAW cell input. Treat lead_id as text and maintain one row per
lead_id. Reads return all matches so conflicting rows can be detected. Contact
data is allowed for CRM operations; do not store the original message, dedup_key,
credentials, headers, internal prompts, or raw AI response/error data. Restrict
spreadsheet sharing and retention to the business purpose.

Workflow A reuses existing rows without overwriting approval or delivery fields.
Workflow B updates only status/timestamp/notes fields on the existing lead_id.
Do not manually clear sent/sending to force a retry before checking provider
delivery. A reviewer rejection after a previous send cannot undo delivery.
