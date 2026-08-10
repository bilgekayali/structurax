# Security Policy

## Reporting a vulnerability

Please use GitHub's **Report a vulnerability** flow under the repository's Security tab to submit a private security advisory. Do not disclose an unpatched vulnerability in a public issue, discussion, pull request, or social post.

Include the affected version, reproducible steps, expected impact, and a minimal proof of concept that uses synthetic data. Remove credentials, tokens, personal information, banking data, and proprietary documents before submitting.

## Data and execution boundary

StructuraX v0.1 is designed for synthetic, normalized JSON document packs. The loader rejects packs not explicitly marked as synthetic. The engine has no payment, approval, messaging, file-upload, or external model integration.

Do not use the demo as a production security control or submit real operational documents. A finding is a review signal, not proof of fraud or authorization to act.

## Supported versions

Security fixes are applied to the latest released minor version. This project is currently an alpha foundation and does not yet make production-support commitments.

