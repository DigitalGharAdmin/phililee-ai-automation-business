# MB02 Shared Error Handler

Reusable centralized failure notification for all three MB02 workflows.

## Architecture

Error Trigger -> Gmail Send Message

Alerts contain workflow name, failed node, execution ID, execution mode, retry
reference when present, execution link, and a fixed generic error summary. They
intentionally use fixed safe summaries rather than raw upstream error messages.
Submitted form data, source email body/snippet, request payloads, private source or
recipient addresses, credentials, and tokens are excluded from the alert content.
The private notification destination is replaced in portfolio evidence.

## Verified acceptance evidence

The project owner reported these manual tests; documentation closure verifies
exported configuration and does not rerun live services.

- Sample Error Trigger notification: PASS.
- Workflow 1 production failure notification: PASS.
- Workflow 2 controlled parser failure notification: PASS.
- Workflow 3 production OpenAI failure notification: PASS.

## Safe portfolio evidence

`mb02_shared_error_handler.sanitized.json` preserves the connected node graph and
safe alert expressions. Original node IDs are replaced with synthetic IDs; Gmail
credentials, workflow/version/instance identifiers and webhook identifiers are
removed. The raw export remains ignored and local-only.

Configure a local Gmail credential and replace the reserved example recipient
before activation. Import this handler and select it as the error workflow for
each main workflow, replacing `CONFIGURE_SHARED_ERROR_HANDLER`. Execution metadata
and links are populated at runtime; no real execution identifiers are committed.
