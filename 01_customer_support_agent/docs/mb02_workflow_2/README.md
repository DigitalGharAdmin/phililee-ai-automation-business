# MB02 Workflow 2 — Gmail AI Classification → Google Sheets

## Purpose

This n8n workflow automatically receives incoming Gmail messages, classifies them
with an AI model, parses the structured classification, and records the result in
Google Sheets. It demonstrates a reusable commercial pattern for inbox triage,
customer-support routing, and lead or operations monitoring.

## Workflow Architecture

```text
Gmail Trigger
  → OpenAI: Message a model
  → Code in JavaScript
  → Google Sheets: Append row
```

The Gmail Trigger detects a new message. The OpenAI node returns a structured JSON
classification. The JavaScript node parses and normalizes that result before the
Google Sheets node appends a reporting row.

## Email Classification Output

The workflow produces these structured fields:

| Field | Purpose |
| --- | --- |
| `category` | Business category assigned to the incoming message |
| `priority` | Processing urgency assigned by the AI model |
| `summary` | Concise description of the message and required attention |
| `status` | Workflow processing or triage state |

Supported category values:

- `support`
- `sales`
- `order`
- `billing`
- `complaint`
- `spam`
- `general`

Supported priority values:

- `low`
- `medium`
- `high`

## Google Sheets Schema

Each completed execution appends one row with these columns:

| Column | Content |
| --- | --- |
| `timestamp` | Time the workflow processed the message |
| `sender` | Sender value supplied by the Gmail trigger |
| `subject` | Incoming email subject |
| `snippet` | Short source-message preview |
| `category` | Parsed AI category |
| `priority` | Parsed AI priority |
| `summary` | Parsed AI summary |
| `status` | Parsed workflow status |

## Verified Functional Test

The workflow was manually verified end-to-end with the following results:

- Gmail OAuth connected successfully through n8n's credential manager.
- Gmail Trigger fetched incoming email data successfully.
- AI classification produced structured JSON.
- The JavaScript step separated `category`, `priority`, `summary`, and `status`.
- Google Sheets appended the mapped row successfully.
- A real incoming email triggered the published workflow automatically.
- An urgent refund/billing test message was classified as `billing` with `high`
  priority and logged successfully.

The test evidence intentionally excludes the sender address and all private account
identifiers.

## Security

- Credentials remain in n8n's credential manager and are not stored in repository
  files.
- The original n8n export is intentionally local-only and excluded from Git.
- Only the sanitized workflow export is suitable for committing.
- Credential references, workflow/instance identifiers, and Google resource IDs are
  removed from the sanitized export.
- Test evidence must not include private email addresses, OAuth data, access tokens,
  API keys, passwords, or account identifiers.
- Credentials and destination resources must be configured again after importing the
  sanitized workflow.

## Evidence Files

- `README.md`
- `mb02_workflow_2_gmail_ai_classification_sheets.sanitized.json`

Together these files document the verified workflow and preserve its reusable node
graph, classification prompt, JavaScript parsing logic, and sheet-column mapping.
The original exported workflow remains local-only and uncommitted.
