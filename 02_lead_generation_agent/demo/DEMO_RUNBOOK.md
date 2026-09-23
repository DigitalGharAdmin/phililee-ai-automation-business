# Lead Agent portfolio demo runbook

This runbook presents the completed Lead Generation portfolio build.
Default presentation uses synthetic local API calls, offline workflow simulation
and existing sanitized manual acceptance evidence. No live action is required.

1. From the repository root, start the backend in PowerShell:

   ```powershell
   cd 02_lead_generation_agent
   $env:DATABASE_URL = "sqlite:///./demo_local.db"
   $env:OPENAI_API_KEY = ""
   .\.venv\Scripts\python.exe -m uvicorn app.api:app --reload
   ```

   The explicit empty key overrides .env and ensures predictable offline fallback.
   Use a new disposable database filename if this demo database already has leads;
   never delete the developer database to prepare a demo. Stop with Ctrl+C.
2. Open Swagger at http://127.0.0.1:8000/docs. Show qualification, capture and GET
   endpoints with [synthetic scenarios](DEMO_SCENARIOS.md); avoid listing real leads.
3. Open the existing local n8n installation using its established startup method.
   No n8n install command or instance URL is assumed. Open the two clean workflows;
   do not activate, edit credentials or execute live for this offline presentation.
4. Show Workflow A's intake diagram and HOT/WARM/COLD inputs. Run
   `node n8n/tests/validate_workflows.mjs` to demonstrate simulated routing and reuse.
5. Show the CRM column specification and sanitized acceptance text, not a private
   Sheets tab. Explain pending/awaiting_approval versus not_required/nurture.
6. Show Workflow B's protected approval form configuration and required lead_id.
   Never reveal Basic Auth credentials or an authenticated form URL with secrets.
7. Walk through rejection: eligible lookup, rejected/not_sent, no Gmail.
8. Walk through approval: sending marker, Gmail, sent timestamp. Use the offline
   simulation and prior evidence rather than clicking Execute on live Gmail.
9. Show the textual real-delivery confirmation from Build 4. No new delivery is
   claimed. A future live delivery demo needs separate authorization and a private
   controlled recipient; example.com inputs must not be used as delivery targets.
10. Demonstrate repeated approval using the offline fixture: already_sent, no send,
    unchanged CRM. Explain concurrency and ambiguous-send retry limitations.
11. Show fallback using the empty process key above: capture still succeeds with
    deterministic fields. To restore .env configuration, stop the server, remove
    only the demo process overrides and restart from the same project environment:
    `Remove-Item Env:OPENAI_API_KEY` and `Remove-Item Env:DATABASE_URL`.
12. Show clients the problem, qualification rationale, human control, CRM states,
    duplicate handling, test results and evidence. Do not promise production SLAs.
13. Never display .env, credential dialogs, OAuth tokens, private execution history,
    personal inboxes, actual contact rows, raw exports, database contents or debug
    dumps. Use textual sanitized evidence; keep any private screenshots outside Git.

For a separately authorized live demonstration, recheck local credentials, backend
reachability and Sheets mappings first, then follow scenarios 1-8 sequentially.
Do not retry uncertain sends blindly. This runbook does not authorize live actions.
