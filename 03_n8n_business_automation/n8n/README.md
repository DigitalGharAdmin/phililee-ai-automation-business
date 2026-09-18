# Planned n8n package

Build 2 provides an inactive [core workflow](workflow_core/README.md).
The [error handler](workflow_error_handler/README.md) remains a Build 3 design handoff.
Native import compatibility and live acceptance must be checked before activation.
Only reviewed `*.sanitized.json` exports may be committed. Place local raw exports
under `n8n/raw_exports/` (ignored); never export credentials into this repository.
Configure providers through n8n credentials locally, not inline node parameters.
Offline contract/privacy checks: `node scripts/validate.mjs` from the project root.

Full checks: `node n8n/tests/validate_workflows.mjs`. Regenerate the export with
`node scripts/build_core.mjs`. No real n8n, OpenAI, Gmail or Sheets action was
performed during Build 2. Configure all credentials locally after importing.
