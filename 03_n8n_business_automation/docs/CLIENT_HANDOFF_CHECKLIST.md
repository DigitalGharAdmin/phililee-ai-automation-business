# Client handoff checklist

Use with [onboarding](CLIENT_ONBOARDING.md); no secret values belong in this checklist.

- [ ] Client config, route ownership, approved acknowledgement wording and response version finalized.
- [ ] Client-owned credentials created privately; access/rotation owner recorded outside Git.
- [ ] Client's Google Sheet and Requests tab prepared; all 24 columns and request_id mappings verified.
- [ ] Core and matching error handler imported inactive; correct credentials bound on every external node.
- [ ] Handler published for authorized testing; Error Workflow assigned and saved; core then published.
- [ ] Unique production webhook path, registration, HTTPS and authentication verified.
- [ ] No-send smoke test passed before enabling outbound mail.
- [ ] Explicitly authorized email acceptance passed with a controlled recipient and approved wording.
- [ ] Duplicate test preserved sent_at and produced no second send.
- [ ] Clear and ambiguous failure behavior reviewed using offline simulation or authorized test setup.
- [ ] Reconciliation procedure reviewed and an operator assigned; no automatic unknown-state resend.
- [ ] Operator notification setting/recipient reviewed privately; disabled behavior confirmed.
- [ ] Demo flags restored; intended production flags explicitly agreed rather than copied from a send test.
- [ ] Configuration, schema, limits, evidence and operating documentation delivered.
- [ ] Client backup/export and recovery procedure agreed; private exports remain outside the public repository.
- [ ] [Production readiness checklist](PRODUCTION_READINESS_CHECKLIST.md) reviewed and outstanding items accepted.

Handoff is not a guarantee of production reliability. Capture acceptance decisions
and operating ownership privately without storing credentials in project documents.
