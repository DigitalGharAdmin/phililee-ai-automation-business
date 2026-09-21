# MB05 Business Automation — Error Handler

Build 3 inactive sanitized workflow: business_automation_error_handler.sanitized.json.
Error Trigger -> Normalize Error Context -> Prepare Privacy-Safe Error Notification
-> Notify Operator? -> optional Gmail -> fixed Notification Outcome.
Disabled notifications flow through Notification Disabled -> Notification Outcome
and preserve notification_status=disabled. Notify Operator? explicitly has Always
Output Data OFF so no empty item leaks into its true branch. Errors never retry business work.

Import this workflow, then select it in the core Settings > Error Workflow. Do not
assign it to itself. No real workflow IDs or credentials are present. Native trigger
assignment passed operator live Test A; verify it for each new deployment.
Handled external error branches can finish without triggering a workflow-level error.

Normalize Error Context emits only a fixed workflow label, an allowlisted core node
name or Unknown stage, allowlisted mode and fixed category. It never copies raw
errors, request bodies, contact fields, execution URLs/IDs or credential objects.
The notification summary is fixed; no user-controlled text is concatenated.

Notifications are disabled in the trusted config literal. To prepare a separately
authorized test, replace the example recipient locally, select native Gmail OAuth
and explicitly enable notifications. The unchanged example recipient is blocked.
Gmail retries are disabled. A failed/empty acknowledgement yields unconfirmed without
recursive retries; no failure data is forwarded. Core enable flags do not enable this
handler. Raw trigger input may be visible in the private editor: keep access and
retention restricted even though saved execution data is disabled in the export.

Generate using node scripts/build_error_handler.mjs after generating the core so
its node-name allowlist stays current. Validate using node n8n/tests/validate_workflows.mjs.
See [reliability](../../docs/BUILD_3_RELIABILITY.md) and
[manual test plan](../evidence/BUILD_3_MANUAL_TEST_PLAN.md). The operator reported live Test A PASS; this synchronization ran offline only.
