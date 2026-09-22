# Final acceptance matrix

PASS means the stated scope passed. Live columns refer only to operator-reported
historical tests; they do not certify every configuration or production deployment.
Build 5 introduced no new live tests. Plans alone are never used as PASS evidence.

| Capability | Offline validation | Live acceptance | Evidence | Status |
| --- | --- | --- | --- | --- |
| Foundation/contracts | PASS: strict fields and fixed summaries | Build 2 valid/invalid | [B2](../n8n/evidence/BUILD_2_MANUAL_ACCEPTANCE.md) | PASS |
| Validation/no-send | PASS: rejects malformed fields; no provider work | Build 2 invalid/no-send | [B2](../n8n/evidence/BUILD_2_MANUAL_ACCEPTANCE.md) | PASS |
| Routing | PASS: deterministic/client mappings | Build 4 support_desk/sales_team | [B4](../n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md) | PASS |
| AI fallback | PASS: disabled, transport, malformed and refusal simulations | Build 3 B transport failure only; no real OpenAI call | [B3](../n8n/evidence/BUILD_3_LIVE_ACCEPTANCE.md) | PASS for fallback |
| Google Sheets logging | PASS: mappings, confirmation and failure | Builds 2/4 success; Build 3 C failure | [B3](../n8n/evidence/BUILD_3_LIVE_ACCEPTANCE.md), [B4](../n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md) | PASS |
| Email send | PASS: policy/confirmation gates with fake Gmail | Build 2 send; Build 4 E custom content | [B4](../n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md) | PASS |
| Clear Gmail failure | PASS: conservative rejection and failed persistence | Build 3 D invalid recipient | [B3](../n8n/evidence/BUILD_3_LIVE_ACCEPTANCE.md) | PASS |
| Ambiguous Gmail outcome | PASS: unknown and no resend | Build 3 E unconfirmed final persistence | [B3](../n8n/evidence/BUILD_3_LIVE_ACCEPTANCE.md) | PASS |
| Duplicate after sent | PASS: row/sent_at preserved | Build 3 F; Build 4 F | [B4](../n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md) | PASS |
| Duplicate during sending | PASS: no write/send | Build 3 G | [B3](../n8n/evidence/BUILD_3_LIVE_ACCEPTANCE.md) | PASS |
| Duplicate after unknown | PASS: no downgrade/resend | Build 3 H | [B3](../n8n/evidence/BUILD_3_LIVE_ACCEPTANCE.md) | PASS |
| Error handler | PASS: disabled, accepted/unconfirmed simulations; privacy | Build 3 A / Build 4 G disabled path; enabled alerts not live-claimed | [B3](../n8n/evidence/BUILD_3_LIVE_ACCEPTANCE.md), [B4](../n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md) | PASS for stated scope |
| Client config | PASS: version/schema/secrets and generation | Build 4 A/C imported settings | [B4](../n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md) | PASS |
| Support demo | PASS: exact settings and simulated runtime | Build 4 A/B | [B4](../n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md) | PASS |
| Sales demo | PASS: settings, simulated send and reuse | Build 4 C–F | [B4](../n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md) | PASS |
| Secret safety | PASS: pattern/config/placeholder scans | Build 4 H manual spot-check; not exhaustive detection | [B4](../n8n/evidence/BUILD_4_LIVE_ACCEPTANCE.md), [B5](../n8n/evidence/BUILD_5_FINAL_VALIDATION.md) | PASS for scan scope |
| Privacy safety | PASS: safe errors and synthetic/publication checks | Build 3 safe error handling; Build 4 G/H | [B3](../n8n/evidence/BUILD_3_LIVE_ACCEPTANCE.md), [B5](../n8n/evidence/BUILD_5_FINAL_VALIDATION.md) | PASS for reviewed scope |
| Portfolio packaging | PASS: Build 5 checks | Not applicable: offline packaging only | [B5](../n8n/evidence/BUILD_5_FINAL_VALIDATION.md) | PASS |

Not claimed: successful real OpenAI inference, live enabled operator alerts,
production load/availability testing, exactly-once delivery, or implemented approval
resumption. Use [production readiness](PRODUCTION_READINESS_CHECKLIST.md) for deployment work.
