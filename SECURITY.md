# Security Policy

## Supported Versions

This repository is a portfolio of AI automation systems maintained by Phililee AI Labs.

Security fixes and maintenance are provided for the latest version of the `main` branch.

| Version | Supported |
| --- | --- |
| Latest `main` branch | ✅ |
| Older historical snapshots or commits | ❌ |

## Reporting a Vulnerability

If you discover a security vulnerability in this repository, please do not disclose sensitive details publicly in an Issue.

Please use GitHub's private vulnerability reporting or security advisory features when available.

When reporting a vulnerability, include:

- A clear description of the issue
- The affected project or file
- Steps to reproduce the issue
- The potential security impact
- Any relevant logs or screenshots with secrets and personal data removed

Please do not include:

- API keys
- Access tokens
- Passwords
- OAuth credentials
- Private keys
- Personal email addresses
- Real Google Sheet IDs
- Customer or client data
- Any other sensitive information

## Scope

This policy applies to the public source code and documented workflows in this repository, including:

- `01_customer_support_agent`
- `02_lead_generation_agent`
- `03_n8n_business_automation`

External services such as OpenAI, Gmail, Google Sheets, n8n hosting, databases, or third-party infrastructure may have their own security policies.

## Security Practices

This repository is designed to keep sensitive configuration outside the committed source code.

Examples include:

- Local `.env` files are excluded from Git
- Runtime databases and private exports are excluded
- Public workflow artifacts are sanitized
- Credentials are bound externally
- Public examples use synthetic data
- Secret and privacy scans are used before publishing changes

## Response

Phililee AI Labs will review reported vulnerabilities and determine whether they affect the current supported repository state.

Response and remediation timing may vary depending on the severity and complexity of the issue.

Thank you for helping keep this project secure.
