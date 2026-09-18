# Build 5 reliability and packaging audit

Scope: MASTER BUILD 04 internal Build 5. MASTER BUILD 05 is not started.
Recorded 2026-09-18. Backend and workflow logic remain unchanged.

## Regression coverage

| Area | Evidence |
| --- | --- |
| Build 1 | test_scoring: rubric bands, thresholds, combinations, repeatability; test_models/test_api: normalization, minimal fields, invalid enum/email, endpoint validation |
| Build 2 | test_persistence: capture/GET/list, normalized dedup, distinct services, immutable duplicates, unique constraint and simulated stale-lookup race, safe DB errors, reconnect persistence |
| Build 3 | test_ai: strict model, malformed/refused/timeout/auth/rate/service responses using in-memory SDK transport, payload minimization, reconciliation bounds, AI persistence and duplicate skip |
| Local settings | test_settings: isolated temporary project copies, .env absent/present, explicit and empty environment overrides, app startup; real .env never read by these subprocess checks |
| Build 4 | validate_workflows.mjs: required form field names, auth, decision options, CRM lead_id matching, routing and no-write reuse, retry configuration, approve/reject/guard behavior |
| Build 5 additions | test_reliability: identity/score/enum injection rejected during persisted capture; deterministic fallback, timestamp validity and duplicate AI skip; safe unknown-ID response |
| Workflow additions | missing/malformed ID and excessive notes stop before external work; populated sent timestamp blocks both approve and reject without writes |

Python result: 119 collected, 119 passed, 0 failed. One existing dependency
deprecation warning does not affect the result. Static result: both workflow JSON
files parse and 31 offline scenarios pass. Tests use isolated databases and fake
providers; no live n8n, Gmail, Sheets or paid AI requests were performed.
Race coverage exercises database uniqueness/recovery, not a distributed load test.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node n8n/tests/validate_workflows.mjs
.\.venv\Scripts\python.exe scripts/audit_publication.py
git diff --check
```

The publication audit scans project tracked and nonignored candidate files for
provider tokens, private keys, bearer tokens, secret assignments, nonexample email
addresses, raw workflows/credential references, database/env files and debug dumps.
It verifies local env/database ignore rules. Findings print paths/categories only.
Manual review supplements pattern checks; no scanner proves absence of every secret.
Ignored private .env/database content and other projects are outside the scan scope.
Existing synthetic test domains are allowed; all new demo addresses use example.com.

## Acceptance and limitations

Build 4 live evidence is operator-reported and indexed in
[the evidence index](../n8n/evidence/README.md). Build 5 adds offline regression and
presentation artifacts, not new live delivery evidence. Synthetic scenarios use
fallback to make labels reproducible; real AI may change final qualification within
its bounded rules. A sent-state guard does not prove concurrent exactly-once delivery.
Production auth, deployment/migrations and transactional messaging remain out of scope.

MASTER BUILD 04 internal Builds 1-5 are complete following clean validation and
local commit. Next master step: MASTER BUILD 05 - n8n Business Automation; no files
or systems for that step are created by this work.
