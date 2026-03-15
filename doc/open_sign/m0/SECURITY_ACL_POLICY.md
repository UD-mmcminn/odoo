# Open Sign Security ACL And Record Rule Policy

Status: Finalized for M0 (`T94`); current portal OTP/idempotency ORM posture enforced in `T39` / `T316`
Date: 2026-03-15

## Security Groups

- `open_sign.group_open_sign_user`
- `open_sign.group_open_sign_manager`
- `open_sign.group_open_sign_auditor`
- `base.group_portal` (token-scoped, controller-mediated only)

## Model Access Matrix (v1)

| Model | User | Manager | Auditor | Portal |
|---|---|---|---|---|
| `open.sign.template` | R/W/C | R/W/C/D | R | None |
| `open.sign.role` | R/W/C | R/W/C/D | R | None |
| `open.sign.template.field` | R/W/C | R/W/C/D | R | None |
| `open.sign.template.field.option` | R/W/C | R/W/C/D | R | None |
| `open.sign.request` | R/W/C (owned/company) | R/W/C/D | R | None |
| `open.sign.request.signer` | R/W/C (request scope) | R/W/C/D | R | Read/write only through token-validated controller flow |
| `open.sign.request.value` | R/W/C (request scope) | R/W/C/D | R | Write only via token-validated controller flow |
| `open.sign.audit.log` | R | R/W/C (restricted maintenance only) | R | None |
| `open.sign.otp.challenge` | None | None | None | Route-mediated OTP actions only; ORM access remains system-only because the model stores OTP verification internals (`code_hash`, `code_salt`) rather than operator-facing business records |
| `open.sign.portal.idempotency` | None | None | None | Route-mediated replay handling only; ORM access remains system-only because the model stores replay state and exact response payloads (`response_json`) |

`open.sign.otp.challenge` is enforced in the current repo with:
- one explicit ACL row for `base.group_system`
- a company-scoped system record rule
- field-level restriction on `code_hash` / `code_salt` to `base.group_system`

`open.sign.portal.idempotency` is enforced in the current repo with:
- one explicit ACL row for `base.group_system`
- a company-scoped system record rule
- field-level restriction on `response_json` to `base.group_system`

## Deferred Portal Model Candidates

The following models are still documented as future hardening candidates, but they are **not implemented in the current repo** and therefore are not part of the active Phase 3 runtime surface or current `T39` model scope.

| Model | Status | Notes |
|---|---|---|
| `open.sign.signing.session` | Future hardening candidate | Optional session-tracking hardening if later token/session expiry or stronger per-visit forensic/session-state needs justify a dedicated model. |

## Record Rule Policy

- All business models with `company_id` require explicit company isolation rule.
- User role is restricted to owned/assigned records in allowed companies.
- Auditor role is read-only across allowed company scope.
- Portal users have no generic model write ACLs for signing data; writes are route/token gated.

## Controller-Side Security Rules

- All public signer endpoints must perform token access checks with constant-time comparison semantics.
- Mutating endpoints must enforce signer state gate + request status gate + idempotency key checks.
- Decline/submit actions must be concurrency-safe to prevent double transitions.

## Audit Immutability Policy

- Audit entries are append-only after request reaches `completed` or `voided`.
- Any exceptional repair requires manager-only action and creates an explicit repair audit event.

## Required Tests

- ACL tests for each internal group and model.
- Multi-company boundary tests.
- Portal token replay/expiry/abuse tests.
- Race-condition tests for submit/decline with concurrent requests.
