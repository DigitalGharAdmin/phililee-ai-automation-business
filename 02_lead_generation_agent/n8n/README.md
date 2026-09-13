# Build 4: lead routing and approved follow-up

Implementation and offline/static validation: complete. **Manual n8n acceptance:
pending.** These are inactive import-ready templates, not exports from the user's
live instance. No live service was called during implementation.

```text
Lead source -> Workflow A webhook -> FastAPI /leads?use_ai=true
 -> deterministic + optional AI qualification -> stored final qualification
 -> Google Sheets CRM -> Workflow B human approval -> Gmail -> CRM sent status
```

FastAPI is the qualification and persistence source of truth. Google Sheets is
the MVP CRM log; n8n orchestrates routing and outbound communication. Hot/warm
leads require human approval. Cold leads are logged for nurture and cannot enter
the email path. No backend changes are required.

## Import and local configuration

1. Import [Workflow A](workflow_a_lead_intake/lead_intake_routing.sanitized.json)
   and [Workflow B](workflow_b_approval_followup/approval_followup.sanitized.json).
   Keep both inactive until manual tests pass.
2. Create a private Google spreadsheet and a tab named `Leads`, with exactly the
   headers in [CRM columns](google_sheets/crm_columns.md). Use the same sheet/tab
   in every Google Sheets node. Replace `YOUR_GOOGLE_SHEET_ID` locally.
3. Select local Google Sheets OAuth credentials in every Sheets node, Gmail OAuth
   in Workflow B, and a reviewer-only HTTP Basic Auth credential in its Form node.
   Credential references are intentionally omitted. No credential is created here.
4. Confirm each Sheets mapping after selecting the sheet. Match only on `lead_id`;
   reads return all matches, and write cell format is **RAW** to avoid interpreting
   untrusted CRM strings as spreadsheet formulas. Keep only the listed mappings.
5. Start the existing FastAPI app as documented in the project README. HTTP nodes
   use `http://127.0.0.1:8000`; this works only when both runtimes can reach that
   same host. For containers/remote n8n, configure a reachable private backend URL
   in both HTTP nodes. Do not expose the unauthenticated backend publicly.
6. Verify trigger response modes, branch output order, field mappings and Gmail
   options in your installed n8n before enabling either workflow.

No n8n executable/global package was found in the checked local command/global
package locations. The running instance version was not queried. Templates target
standard node versions: Webhook 2, HTTP Request 4.2, Code 2, IF 2.2, Google Sheets
4.6, Gmail 2.1, Respond to Webhook 1.4 and Form Trigger 2. Form Trigger 2 intentionally
supports `responseNode` for the custom completion result. If your instance upgrades
that node, confirm response behavior in the UI (or use its supported Form ending
node). Exact native-export compatibility and credential execution remain manual
acceptance items. n8n was not launched, upgraded, modified or published.

The Sheets node supports append-or-update by a matching column; it is not a
transactional unique constraint. See the [official Sheets source](https://github.com/n8n-io/n8n/blob/master/packages/nodes-base/nodes/Google/Sheet/v2/actions/sheet/appendOrUpdate.operation.ts)
and [Form Trigger documentation](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.formtrigger/).

## Reliability and operator controls

HTTP, Sheets and Gmail nodes retry up to 3 attempts with 2000 ms waits, then stop
the workflow. Code nodes are deterministic and are not retried. HTTP nodes have a
60-second timeout and do not enable Never Error. A failed lookup/update cannot
continue to Gmail. Only a successful Gmail node can reach the sent-status update.

Before Gmail, Workflow B writes `sending`. Existing `sent`, a populated sent
timestamp, or `sending` blocks another attempt. If sending or the later Sheets
update fails, review the actual provider outcome and CRM manually before changing
that status. Do not blindly retry an entire execution from the Gmail node.

**Limitations:** Gmail's required node retries may send more than once after an
ambiguous remote success. Lookup/upsert and lookup/mark/send are not atomic.
Concurrent intake can duplicate CRM rows or overwrite newly established status;
concurrent approvals can both pass a stale guard. Run approvals one at a time and
avoid concurrent intake/approval for the same lead during MVP acceptance. Duplicate
CRM keys stop approval, rather than selecting an arbitrary row. A production system
needs transactional delivery state/idempotency before stronger guarantees are made.

The Form uses Basic Auth because possession of a lead ID alone is not approval.
Give access only to authorized reviewers. Use HTTPS or a private local environment;
do not publish an unprotected approval form. Reviewers must inspect the lead in the
CRM/API before submitting approve/reject. This MVP has no named-reviewer audit trail.

## Failure notification and privacy

Optionally select the existing safe shared Error Workflow under each imported
workflow's Settings -> Error Workflow. No cross-workflow ID is invented in these
templates, and no Phase 02 workflow is modified. Alerts must use only safe
operational metadata and a fixed generic summary. Do not forward raw upstream
error messages, lead messages, email bodies, recipient data, headers or payloads.

Normal n8n node execution contains prospect data and, after Gmail, message data.
Templates disable saved successful/error/manual execution data and progress where
supported; verify local retention settings and avoid sharing raw execution views.
Gmail/HTTP/Sheets native errors may contain private details in the local editor:
never forward them verbatim. CRM stores necessary contact/profile data and bounded
AI summary, not the original lead message, internal prompts, raw AI responses or
errors, dedup hashes or credentials. Notes must contain only necessary reviewer
context. Review AI summary text for unexpected personal information before sharing.

## Offline verification and manual acceptance

```powershell
node n8n/tests/validate_workflows.mjs
.\.venv\Scripts\python.exe -m pytest -q
```

The Node script checks JSON, connections, retries, mapping keys and Code-node
behavior using in-memory HTTP/Sheets/Gmail substitutes. It is not an n8n runtime
emulator and cannot prove provider execution, authentication or import behavior.
The Python suite verifies the unchanged backend without real OpenAI requests.

Complete both per-workflow checklists before claiming end-to-end acceptance.
Manual tests can invoke paid AI, write CRM data and send email; use authorized test
accounts and fictional lead data. Store only sanitized evidence in `evidence/`.
Do not place raw exports, credentials or personal screenshots in this directory.

Next: Build 5 — Reliability Tests, Demo Evidence, and Portfolio Packaging.
