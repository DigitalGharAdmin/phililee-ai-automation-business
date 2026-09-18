# Planned n8n package

Build 1 defines architecture only. Build 2 will implement [core](workflow_core/README.md)
and [error handling](workflow_error_handler/README.md). No workflow is importable yet.
Only reviewed `*.sanitized.json` exports may be committed. Place local raw exports
under `n8n/raw_exports/` (ignored); never export credentials into this repository.
Configure providers through n8n credentials locally, not inline node parameters.
Offline contract/privacy checks: `node scripts/validate.mjs` from the project root.
