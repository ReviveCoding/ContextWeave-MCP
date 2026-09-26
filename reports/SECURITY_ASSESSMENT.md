# Security assessment

## Status

The confirmatory security experiment E19 was `NOT RUN / GATED` after the pre-freeze power closure. No production security certification is supported. No protected benchmark was created or accessed.

## Implemented software controls

The source tree contains AST-based read-only SQL validation, signed JWT checks, tenant/account scoping, and governed cache identities. Unit tests exercise representative SQL attack rejection, wrong audience, expired credentials, role checks, tenant separation, scope separation, and freshness-key invalidation. MCP transport smoke evidence covers in-memory, stdio, and Streamable HTTP discovery/tool calls.

These checks establish software behavior on the tested cases. They are not an executed E19 adversarial campaign, penetration test, authorization proof, or security hard-gate result. `UnauthorizedExposure = 0`, `CrossTenantLeak = 0`, and `CriticalExfiltration = 0` were never evaluated on a protected final benchmark.

## Unexecuted evidence

Prompt-injection campaigns, malicious tool metadata, cache poisoning, schema/metric poisoning, oversized outputs, network exfiltration, compound OOD attacks, and final security gate matrices are `NOT RUN / GATED`. Figure F11 records this status without imputing zero incidents.

## Claim boundary

V1 closed as `V1_PRE_FREEZE_INSUFFICIENT_POWER`. The original v2 E07 is `SUPERSEDED_INVALID_CALIBRATION`; corrected v2 still had insufficient power and closed as `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`. The +13.06 percentage-point difference is qualification-only and provides no security or efficacy evidence. No Amazon-internal, production, advertiser, external-transfer, or security-certification claim is supported.
