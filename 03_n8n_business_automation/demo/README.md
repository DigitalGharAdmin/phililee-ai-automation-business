# Synthetic contract examples

`contracts.json` contains a fictional example.com inquiry and its expected result
with email disabled. Run `node scripts/validate.mjs` to check it without network
access. It is not evidence of a provider action or a command to send email.

Build 2 fixtures in `n8n/tests/validate_workflows.mjs` vary this input for sales,
support, missing request_id, invalid email, requires_response=false, AI fallback,
duplicate IDs and complaint/billing no-send. Additional scenarios cover provider
failures and conflicting rows. Run `node n8n/tests/validate_workflows.mjs`.
All external operations are in-memory substitutes, never real provider requests.

For the complete portfolio presentation, use [scenarios](DEMO_SCENARIOS.md),
[the runbook](DEMO_RUNBOOK.md) and the sample_payloads folder. Run
`node n8n/tests/validate_portfolio.mjs --show-demo` for nine labeled offline scenarios
plus invalid input. No provider action occurs. Simulated timestamps reflect the local
run time; payloads, expected states and generated artifacts are deterministic.
