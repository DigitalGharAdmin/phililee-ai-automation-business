# Build 3 live reliability acceptance

MASTER BUILD 05 — n8n Business Automation, internal Build 3.
Acceptance is COMPLETE based on the operator's supplied live results A–H.
This record contains sanitized outcomes only. The repository synchronization ran
offline; it did not repeat live tests or access n8n, OpenAI, Gmail or Sheets.
Build 4 — Client Customization Layer is next and has not started.

TEST_A_SHARED_ERROR_HANDLER: PASS

An intentional core failure automatically invoked the linked handler. Allowlisted
privacy-safe context reached Notification Outcome with notification_status=disabled;
no notification was sent. Live fixes disabled Always Output Data on Notify Operator?,
connected Notification Disabled to Notification Outcome and preserved disabled.

TEST_B_OPENAI_FAILURE_FALLBACK: PASS

A temporary unreachable local endpoint produced a safe transport failure with AI
enabled. Deterministic support/normal/support_queue continued, logged=true,
email_status=not_requested, result_summary=recorded, ai_status=unavailable. No raw
error reached the caller and no real OpenAI or Gmail call occurred. The endpoint
was restored to https://api.openai.com/v1/responses and all three core flags
(email_enabled, acknowledgement_policy, ai_enabled) were restored to false.

TEST_C_GOOGLE_SHEETS_FAILURE: PASS

A non-existent logging tab produced accepted=true, classification=billing,
route=review_queue, logged=false, status=failed, email_status=not_requested and
result_summary=operation_failed. No new row or Gmail send occurred; the result
contained no raw Google error. Restoring Requests cleared mappings in n8n; all
24 mappings were restored. The generator and validator now protect every mapping.

TEST_D_GMAIL_CLEAR_FAILURE: PASS

A temporary invalid recipient returned the generic validation error
`Invalid email address (item 0)`. The clear failure branch persisted and confirmed
failed_safe/not_sent/send_failed, logged=true, action=acknowledge, accepted=true,
with blank sent_at. No mail was sent. Confirmation uses Boolean semantics and
the full prepared result is restored before final output. Only required state
and timestamp fields are updated; unrelated fields remain intact.

TEST_E_GMAIL_AMBIGUOUS_OUTCOME: PASS

The operator allowed a real test delivery while temporarily making Mark Sent match
a non-existent request. Unconfirmed final persistence yielded needs_reconciliation,
logged=true, unknown and reconciliation_required, with no automatic resend or false
sent confirmation. The row retained safe reconciliation state. The request_id
expression referencing Prepare Business Response was restored after testing.

TEST_F_DUPLICATE_AFTER_SENT: PASS

Replay returned reuse/duplicate, logged=true, email_status=sent and existing_request.
Prior delivery state and sent_at remained intact; no second mail was sent.

TEST_G_DUPLICATE_WHILE_SENDING: PASS

A temporarily seeded sending state returned reuse/duplicate, logged=true,
email_status=sending and existing_request without executing Gmail or changing the
state. The temporary sheet value was restored afterward.

TEST_H_DUPLICATE_AFTER_RECONCILIATION: PASS

Replay of needs_reconciliation/unknown returned reuse/duplicate, logged=true,
email_status=unknown and existing_request. It neither resent nor downgraded or
overwrote the persisted reconciliation state.

## Repository verification and limits

Both inactive sanitized exports are generated from checked-in builders. Offline
validation executes their actual Code nodes and expressions with fake providers:
130 checks passed (19 contract, 102 core, 9 handler), zero failed, plus static
graph/mapping checks and publication secret/privacy checks. The conservative
classifier accepts only known recipient rejection phrases with an optional item
suffix; unfamiliar or contextual error text remains ambiguous. The existing
success acknowledgement gate remains before Mark Sent to catch empty responses.

Sheets and Gmail are not transactional. Sequential duplicate protection does not
guarantee exactly-once delivery or race safety. Serialize intake/operator edits;
unknown outcomes require private operator reconciliation and never auto-resend.
New imports still require credential assignment and local configuration checks.
Raw payloads, credentials, identifiers and screenshots are intentionally excluded.

BUILD_3_LIVE_ACCEPTANCE: COMPLETE
BUILD_3_STATUS: COMPLETE
