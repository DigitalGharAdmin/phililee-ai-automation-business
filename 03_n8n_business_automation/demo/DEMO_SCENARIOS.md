# Deterministic demo scenarios

Run `node n8n/tests/validate_portfolio.mjs --show-demo` from the project directory.
It executes actual exported Code nodes with in-memory provider substitutes. Printed
results are synthetic, not live evidence. No credentials, endpoint or network access
are needed. Each independent scenario starts with empty fake storage; Demo 4 alone
reuses Demo 3's row. Fixture IDs can therefore stay fixed across offline runs.

| Demo | Client / payload | Offline setup | Expected result |
| --- | --- | --- | --- |
| 1. Support, no email | support-demo / [support_request.json](sample_payloads/support_request.json) | Committed defaults | support_desk, log_only, logged, disabled; one row, no mail/AI |
| 2. Sales, no email | sales-demo / [sales_request.json](sample_payloads/sales_request.json) | Committed defaults | sales_team, log_only, logged, disabled; sales-ack-v1 |
| 3. Sales acknowledgement | sales-demo / sales payload | Enable email in memory; policy already true | completed/sent/acknowledgement_sent; custom subject/body, sales-ack-v1; fake sent_at |
| 4. Duplicate after sent | sales-demo / [duplicate_request.json](sample_payloads/duplicate_request.json) | Reuse Demo 3 row and identical input | reuse/duplicate/sent, existing_request; zero writes/sends; sent_at unchanged |
| 5. AI transport failure | support-demo / support payload | Enable AI with synthetic model; fake network error | support_desk, logged, disabled; internal ai_status=unavailable; no raw error |
| 6. Sheets log failure | support-demo / support payload | Fail Log Business Request | failed, logged=false, not_requested, operation_failed; no send |
| 7. Clear Gmail failure | sales-demo / sales payload | Email enabled in memory; fake invalid recipient | failed_safe/not_sent/send_failed; logged=true, sent_at blank |
| 8. Ambiguous Gmail outcome | sales-demo / sales payload | Fake timeout after acceptance | needs_reconciliation/unknown/reconciliation_required; no automatic retry |
| 9. Disabled error notification | sales-demo handler | Synthetic allowlisted context, notifications=false | FALSE branch -> Notification Disabled -> Notification Outcome; disabled, no send |

An additional [invalid payload](sample_payloads/invalid_request.json) deliberately
contains an invalid ID and string boolean. Expect rejected/invalid_input,
logged=false, no provider calls and request_id=null.

The duplicate payload is intentionally byte-for-byte identical to the sales payload:
changing content under the same ID would demonstrate conflict instead. For a new
authorized live demo, prepare fresh UUIDs privately and preserve the entire accepted
payload for replay. Never send to the example.com fixture recipient. Live sends need
separate authorization, a controlled recipient and private credential binding.

AI success, provider failure injection and Gmail outcomes in this run are simulated.
For historical live observations, use the [evidence index](../docs/EVIDENCE_INDEX.md).
