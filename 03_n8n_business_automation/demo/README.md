# Synthetic contract examples

`contracts.json` contains a fictional example.com inquiry and its expected result
with email disabled. Run `node scripts/validate.mjs` to check it without network
access. It is not evidence of a provider action or a command to send email.

Build 2 fixtures in `n8n/tests/validate_workflows.mjs` vary this input for sales,
support, missing request_id, invalid email, requires_response=false, AI fallback,
duplicate IDs and complaint/billing no-send. Additional scenarios cover provider
failures and conflicting rows. Run `node n8n/tests/validate_workflows.mjs`.
All external operations are in-memory substitutes, never real provider requests.
