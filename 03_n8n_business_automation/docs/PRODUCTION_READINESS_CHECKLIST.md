# Demo ready versus production ready

**Demo ready:** sanitized inactive workflows, deterministic client generation,
synthetic scenarios, regression checks and documented prior live acceptance.
These artifacts demonstrate behavior; they do not provision a production service.

**Production ready:** a client-specific deployment has passed its own review,
acceptance and operational handoff. Complete the following before approval:

- [ ] Client-owned credentials, least privilege and credential rotation/revocation plan.
- [ ] Correct production webhook domain, HTTPS, Basic Auth and exposure/access review.
- [ ] Separate test/production environments and isolated per-client Sheets/configuration.
- [ ] Current Sheets authorization, intended document/tab and verified 24-column mappings.
- [ ] Sheets quotas, growth, retention and concurrent-access limitations considered.
- [ ] Intake/operator serialization or a separately designed atomic store for concurrency needs.
- [ ] n8n hosting availability, upgrades and recovery responsibilities agreed.
- [ ] Monitoring expectations, escalation contact and reconciliation owner assigned.
- [ ] Real alert recipient configured privately; disabled/accepted/unconfirmed outcomes understood.
- [ ] Client-approved acknowledgement wording and email policy; no implicit financial/service commitments.
- [ ] Privacy notice, AI opt-in, data access and retention reviewed; free-text redaction limits understood.
- [ ] Backup/recovery plan tested; workflow configuration and private exports secured by the client.
- [ ] No-send, authorized send, duplicate and failure acceptance performed for this deployment.
- [ ] [Handoff checklist](CLIENT_HANDOFF_CHECKLIST.md) completed with documented limitations.

Unknown delivery requires human reconciliation. Sheets/Gmail provide no shared
transaction, and fingerprints are not security controls. The demo has no approval
resumption UI, unattended retry queue or production SLA. This checklist records
engineering work still needed per deployment; it is not certification or legal advice.
