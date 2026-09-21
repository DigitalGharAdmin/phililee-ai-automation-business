# Planned n8n package

Build 2 provides an inactive [core workflow](workflow_core/README.md).
Build 3 adds the [shared error handler](workflow_error_handler/README.md).
Operator Build 3 live acceptance A?H is complete; new deployments still require
local import/configuration checks before activation.
Only reviewed `*.sanitized.json` exports may be committed. Place local raw exports
under `n8n/raw_exports/` (ignored); never export credentials into this repository.
Configure providers through n8n credentials locally, not inline node parameters.
Offline contract/privacy checks: `node scripts/validate.mjs` from the project root.

Full checks: `node n8n/tests/validate_workflows.mjs`. Regenerate the export with
`node scripts/build_core.mjs` and `node scripts/build_error_handler.mjs`. No real n8n, OpenAI, Gmail or Sheets action was
performed during this repository synchronization. Configure all credentials locally after importing.

After import, select MB05 Business Automation — Error Handler in the core
Settings > Error Workflow. No real ID is committed. Keep the handler unassigned
to itself. Notifications and all core enable flags remain off by default.
Current reliability policy is in [Build 3](../docs/BUILD_3_RELIABILITY.md).

See [Build 3 live evidence](evidence/BUILD_3_LIVE_ACCEPTANCE.md). Clear failures use
failed_safe/not_sent/send_failed; ambiguity uses needs_reconciliation/unknown and
operator review. Neither path automatically resends. The disabled error handler
reaches Notification Outcome without sending. Build 4 is not started.
