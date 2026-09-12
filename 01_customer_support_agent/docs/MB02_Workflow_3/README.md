# MB02 Workflow 3 — Form AI Email Automation

## Purpose

This n8n workflow accepts a business inquiry through an n8n Form, generates a
contextual professional reply with OpenAI, and automatically sends the reply through
Gmail. It demonstrates a reusable commercial pattern for inquiry handling, lead
follow-up, and customer communication.

## Workflow Architecture

```text
n8n Form Trigger
  → OpenAI: Message a model
  → Gmail: Send a message
```

## Form Input Fields

The form collects four required fields:

- `Name`
- `Email`
- `Business`
- `Message`

All four fields must be completed before the inquiry is processed.

## AI Processing

OpenAI uses the submitted form context to generate the email body. The response:

- addresses the customer by name;
- acknowledges the submitted business;
- responds directly to the inquiry context;
- explains relevant AI automation benefits where appropriate;
- avoids invented prices, guarantees, delivery dates, or unsupported services;
- contains only the email body; and
- ends with:

```text
Best regards,
Phililee AI Labs
```

## Gmail Automation

The Gmail recipient is mapped dynamically from the submitted `Email` field. The
subject is generated using the submitted `Business` value, and the AI-generated
output becomes the email body. After the preceding nodes complete successfully,
Gmail sends the message automatically.

No real or private recipient address is included in this portfolio evidence.

## Verified Functional Tests

The workflow was manually verified end-to-end:

- The form test submission succeeded.
- The `Name`, `Email`, `Business`, and `Message` output fields were received.
- OpenAI generated a contextual professional response.
- The Gmail send node returned successful message metadata.
- A real email was delivered to the intended recipient inbox.
- Paragraph and newline formatting rendered correctly.
- The delivered email ended with:

  ```text
  Best regards,
  Phililee AI Labs
  ```

- A final execution completed the complete Form → AI → Gmail → Inbox flow.
- The final test used a grocery-store business inquiry and delivered the correctly
  formatted response successfully.

Private recipient and account details are intentionally excluded.

## Security

- OpenAI and Gmail credentials remain in n8n credential storage.
- The raw n8n export remains local-only and is intentionally not committed.
- Only the sanitized workflow export is suitable for repository evidence.
- The sanitized export removes credential references, workflow/instance metadata,
  and webhook/form instance identifiers.
- No API keys, OAuth secrets, tokens, passwords, private email addresses, or account
  identifiers are stored in the committed evidence.
- Credentials must be configured securely in n8n after importing the sanitized
  workflow.

## Evidence Files

- `README.md`
- `mb02_workflow_3_form_ai_email.sanitized.json`

These files preserve the workflow structure, required form configuration, OpenAI
prompt, and safe Gmail expressions for reproducible portfolio evidence.

`MB02 Workflow 3 - Form AI Email.json` is the original local-only export and must
not be committed.

## Reliability hardening and acceptance evidence

Configuration was verified against the final local raw export. The following normal
and controlled-failure results were manually tested and reported by the project
owner; documentation closure does not rerun live services.

External-service nodes use Retry On Fail with 3 attempts and a 2000 ms wait between
attempts, then Stop Workflow after exhausted retries. The sanitized export makes
the default maximum attempts and stop behavior explicit. The shared error workflow
reference is replaced with `CONFIGURE_SHARED_ERROR_HANDLER`.

- Normal Form -> OpenAI -> Gmail: PASS.
- Production OpenAI failure: PASS.
- Shared failure notification: PASS.
- Safe notification excluded submitted form payload and secrets: PASS.
- Model restored to `gpt-4.1-mini`: PASS.
- Final production execution: PASS.
- One unique form submission produced exactly one email: PASS.

This test does not prove full exactly-once delivery under ambiguous remote-write
failures. Production-grade idempotency or delivery deduplication can be added when
required; the observed single email is not an exactly-once guarantee.

Only `mb02_workflow_3_form_ai_email.sanitized.json` is portfolio evidence. Raw exports remain ignored and local-only.
Original node IDs are replaced by synthetic IDs; credentials, resource identifiers,
and instance metadata are removed or replaced. Before import/use, configure local
credentials and destination resources, select the imported Shared Error Handler in
workflow settings, and test in a safe environment before activation.
