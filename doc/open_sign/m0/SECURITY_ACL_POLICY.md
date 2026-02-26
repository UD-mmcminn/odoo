# Open Sign Security ACL And Record Rule Policy

Status: Finalized for M0 (`T94`)
Date: 2026-02-26

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
| `open.sign.signing.session` | None | R/W/C/D | R | Route-mediated signer session updates only |
| `open.sign.otp.challenge` | None | R/W/C/D | R | Route-mediated OTP actions only |
| `open.sign.portal.idempotency` | None | R/W/C/D | R | Route-mediated endpoint replay only |

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
