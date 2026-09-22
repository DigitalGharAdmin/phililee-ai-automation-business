# Portfolio presentation runbook

Default presentation: local files plus offline simulation. Do not open a live inbox,
credential editor, OAuth consent screen or provider console. A future live demo
requires explicit authorization and the [onboarding checklist](../docs/CLIENT_ONBOARDING.md).

Before sharing, close unrelated tabs, clear terminal history from view and use a
clean editor window rooted in this project. Keep personal email, credentials, Basic
Auth values, real Sheet IDs, account names and private execution data off screen.

| Step / click or command | What to say | What the viewer should see |
| --- | --- | --- |
| 1. Open [README](../README.md) | This handles inquiry intake, routing and controlled acknowledgement | Scope, demo clients and limits |
| 2. Open [architecture](../docs/ARCHITECTURE.md) preview | Confirmation gates separate safe completion from uncertainty | Core and handler diagrams |
| 3. Open support config | Client settings are data, not copied business logic | Example Support Co, support_desk, disabled flags |
| 4. Open generated support core JSON or an offline unbound canvas | Same core, client-specific path and data | mb05-support-demo-intake; no credentials |
| 5. Run the command below | These are simulated provider outcomes using the exported code | DEMO_1 support result |
| 6. Read DEMO_1 synthetic_row | The tracking record reflects the selected route | Safe selected row fields; no real Sheet UI needed |
| 7. Open sales config; show DEMO_2 | Sales uses a different queue and response version | sales_team, sales-ack-v1, no email |
| 8. Show DEMO_3 | Email is temporarily enabled only in this in-memory test | completed/sent plus configured subject/body |
| 9. Show DEMO_4 | Same request reuses the sent row | No second send or write |
| 10. Show DEMO_5 through DEMO_8 | Failure states guide recovery rather than hiding uncertainty | Deterministic fallback, failed_safe and reconciliation |
| 11. Open generated handler and show DEMO_9 | Disabled alerts still reach a final outcome | Notification Disabled -> Notification Outcome |
| 12. Show scan/test summary and [evidence index](../docs/EVIDENCE_INDEX.md) | Prior live acceptance and today's simulation are distinct | Paths to sanitized live records, no private dumps |
| 13. Open [onboarding](../docs/CLIENT_ONBOARDING.md) | Credentials and production settings are bound privately | Client config -> generation -> private binding -> acceptance |

```powershell
node n8n/tests/validate_portfolio.mjs --show-demo
```

The terminal labels every result OFFLINE_SIMULATION. Do not present fake-provider
sent status as a new Gmail delivery. For a spreadsheet view, use only a separate
sanitized mock sheet or the synthetic_row output and label it synthetic. No screenshots
are supplied or fabricated by this build. If a separately authorized live demo is
requested, run no-send first, review recipient/wording privately, preserve duplicate
identity and restore email/AI/notification defaults afterward. Do not manufacture
ambiguity by interrupting a real send; use the offline failure scenarios.

End with [client features](../docs/CLIENT_FEATURE_SUMMARY.md),
[handoff](../docs/CLIENT_HANDOFF_CHECKLIST.md) and the
[production-readiness distinction](../docs/PRODUCTION_READINESS_CHECKLIST.md).
