# Security policy

## Reporting a software vulnerability

Use GitHub's private vulnerability-reporting or security-advisory channel for this repository when available. If that channel is unavailable, open a minimal issue requesting private contact and do not include exploit details, credentials, private data, or active tokens.

Include the affected revision, component, reproduction conditions, and expected impact. Do not test against systems or data you do not own or have explicit permission to assess.

## Scientific boundary

This policy covers responsible reporting for the repository's software. It does not mean the system has completed a production penetration test or security certification.

The E19 protected security experiment was **not run** because the v2 program closed before freeze as `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`. Unit tests exercise representative JWT, tenant isolation, cache, and read-only SQL behavior, but they do not establish production hard-gate performance. No claim of zero unauthorized exposure, zero cross-tenant leakage, or zero critical exfiltration is supported for deployment.
