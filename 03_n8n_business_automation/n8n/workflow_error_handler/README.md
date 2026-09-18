# Error workflow handoff

Planned name: Business Automation - Safe Error Handler. Accept workflow failure
events, map them to an allowlisted stage/category and optionally notify a configured
operator. Never interpolate raw error text, payloads, credentials, recipients,
headers or business message content. Notification destinations remain local.
No automatic replay of business actions; ambiguous delivery requires reconciliation.
Build 2 must demonstrate privacy-safe failures offline before live setup.
