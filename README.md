# Phililee AI Automation Business

Professional AI automation portfolio developed under Phililee AI Labs.

This repository contains reusable AI-powered business automation systems designed for freelance client work, business automation, and commercial demonstrations.

## Projects

### 1. AI Customer Support Agent

**Status:** In Development

Current capabilities:

- Customer intent classification
- Order-status request detection
- Complaint and support-request classification
- Priority detection
- Human escalation detection
- Structured customer request extraction
- OpenAI API integration
- Secure environment-variable configuration

### 2. AI Lead Generation Agent

**Status:** Planned

AI-powered system for identifying, qualifying, and organizing potential business leads.

### 3. n8n Business Automation

**Status:** Automation Foundation complete

Business automation workflows integrating AI agents with external services and business processes.

## Technology Stack

- Python
- OpenAI API
- Pydantic
- python-dotenv
- Git
- GitHub
- n8n

## Repository Structure

```text
AI_Freelance_Business/
├── 01_customer_support_agent/
├── 02_lead_generation_agent/
├── 03_n8n_business_automation/
├── demos/
├── docs/
├── portfolio/
├── shared/
├── .gitignore
└── README.md
```

## MASTER PHASE 02 — Automation Foundation: COMPLETE

Completed mini-projects:

1. Webhook -> AI -> Google Sheets.
2. Gmail -> AI Classification -> Google Sheets.
3. Form -> AI -> Email.

The reliability layer includes retries on appropriate external-service nodes, a
reusable Shared Error Handler, safe Gmail failure alerts, controlled failure tests,
restored normal execution tests, and sanitized portfolio evidence. Manual test
results were reported by the project owner; exported configuration is verified
locally. These tests do not establish full exactly-once delivery guarantees.

MASTER PHASE 01: COMPLETE. MASTER PHASE 03 remains planned.
Next roadmap system: `02_lead_generation_agent` — Commercial AI Lead Qualification
and Follow-up MVP.

Evidence: [Workflow 1](01_customer_support_agent/docs/mb02_workflow_1/README.md),
[Workflow 2](01_customer_support_agent/docs/mb02_workflow_2/README.md),
[Workflow 3](01_customer_support_agent/docs/MB02_Workflow_3/README.md), and
[Shared Error Handler](01_customer_support_agent/docs/mb02_workflow_4/README.md).
