# Build 1 scope and handoff

MASTER BUILDS 01-04 are complete per the supplied roadmap. Current work is MASTER
BUILD 05 internal Build 1 only. Repository-level historical status text is outside
this project's edit scope.

Includes commercial service scope, one inquiry-intake MVP, input/output contracts,
deterministic safety rules, configuration proposal, useful folders, synthetic
fixtures and dependency-free offline validation/security checks.

Does not include live n8n workflows, provider calls, Gmail sends, Sheets writes,
credentials, runtime configuration loading, AI model selection, approval UI,
multi-tenant hosting or later master builds. No live evidence is claimed.

## Acceptance

- Scope, architecture, contracts, privacy boundaries and deterministic rules exist.
- Example inputs/outputs and negative contract cases pass offline checks.
- Secret/privacy scan passes; .env/database/raw export ignore rules are checked.
- Only this project's files are committed; no push or live mutation occurs.

## Build 2 handoff

Implement inactive sanitized core and safe-error workflow templates. Select/test
native node versions against the installed n8n instance, authenticate intake, map
these contracts and persist request_id/fingerprint/status in a private test sheet.
Implement bounded AI assistance behind a disabled-by-default switch and deterministic
fallback. Keep email disabled until sender/template policy, authenticated approval,
send-state persistence and sequential duplicate behavior are tested. Validate
provider failures with fakes before separately authorized live acceptance.

Test valid categories, malformed input, conflicting IDs, duplicate replay, AI
failure, logging failure, rejection, approval, disabled response and ambiguous
delivery. Review concurrent execution risk before enabling any real outbound flow.
Resolve client-specific retention, authentication, reviewer access, acknowledgement
policy and local credentials during setup; no client identity is hard-coded here.
