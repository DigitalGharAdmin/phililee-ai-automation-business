# Client onboarding

Use one isolated deployment and private Requests sheet per client. This checklist
does not authorize external actions. Build 4 provides offline generation and tests;
its live acceptance remains planned.

1. Copy `config/client_config.example.json` to `config/client_config.client-slug.json`.
   Private configs are ignored; keep all credentials and real contacts outside them.
2. Set a unique safe client_id and allowed non-secret settings using
   [the configuration contract](CLIENT_CONFIGURATION.md). Start with all feature
   flags false. Review fixed acknowledgement wording and response version.
3. Validate: `node scripts/client_config.mjs config/client_config.client-slug.json`.
   Errors expose only field/category. Correct rejected values before building.
4. Generate: `node scripts/build_client_workflow.mjs config/client_config.client-slug.json`.
   Review the inactive core and handler pair in `n8n/generated/`. Private generated
   artifacts are ignored; only the reviewed support/sales demo pairs are tracked.
5. Run `node n8n/tests/validate_clients.mjs` for offline config, generation, static,
   reliability, secret and privacy checks. Compare private settings against the
   same contract; retain private results outside Git.
6. Import the generated core inactive into n8n; import its generated error handler
   inactive. Check node support and the client-specific webhook path. Avoid deploying
   multiple copies with the same client_id/path.
7. Bind Basic Auth, Google Sheets, Gmail and optional OpenAI through native n8n
   credential selectors. No credentials are inserted by the generator.
8. Select the real Google Sheet manually on every Sheets node and its Requests tab.
   Verify the full 24-column header and every Log Business Request mapping from
   [the core guide](../n8n/workflow_core/README.md); match on request_id and retain
   RAW format. Changing/restoring sheets can clear mappings. Delivery updates must
   not acquire extra blank mappings.
9. Select this client's handler in core **Settings > Error Workflow**. Do not assign
   the handler to itself. No error-workflow ID is included in the export.
10. Confirm all intended safe defaults, disabled save-execution settings, Gmail
    no-retry policy and AI/Sheets 3 tries/2000 ms. Keep notification IF Always Output
    Data OFF. Example recipients remain blocked even with notifications enabled.
11. For separately authorized notifications, set the real operator recipient only
    in the imported handler's trusted config and bind Gmail privately. Never commit
    the resulting private export. AI requires a real model selection and external
    credential; the placeholder keeps it unavailable.
12. Run [manual Build 4 acceptance](../n8n/evidence/BUILD_4_MANUAL_TEST_PLAN.md) in an
    authorized isolated environment. Verify custom content, routing, enablement,
    duplicates, failure states and privacy. Do not infer live success from offline tests.
13. Publish/activate only after explicit acceptance and configuration review. Retain
    sanitized pass/fail evidence; keep private execution data out of Git. No Build 5
    packaging or publication is performed by the Build 4 scripts.

External-only settings: Basic Auth credential, OpenAI key, Gmail and Sheets OAuth
credentials, OAuth secrets, access/refresh/bearer tokens, real Sheet IDs and real
operator recipients. Do not use .env as a workflow loader; none is implemented.

Before replacing a deployment, verify fingerprint compatibility privately, preserve
existing rows and serialize intake/operator updates. Existing sent/sending/unknown
rows are reuse-only, even after config changes. Ambiguous delivery requires operator
reconciliation; Sheets/Gmail do not provide atomic exactly-once delivery.
