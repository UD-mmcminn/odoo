# Open Sign Portal API Contract (v1)

Status: Finalized for M0 (`T95`), runtime-locked in `T38`, idempotency semantics extended in `T316`
Date: 2026-03-15

## Conventions

- Protocol: Odoo `jsonrpc` for mutating signer operations.
- Auth: signer-scoped public token or the approved authenticated internal signer fallback where the route currently allows it.
- Timestamp policy: server UTC is authoritative.
- Concurrency: mutating calls include `request_revision`; stale revisions fail.
- Idempotency:
  - `save` validates `idempotency_key` format only.
  - `submit` and `decline` use durable idempotency with committed-success replay semantics.

## Endpoints

### `POST /my/sign/<int:signer_id>/save`

Request:

```json
{
  "values": [{"field_id": 123, "value": "..."}],
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440010",
  "request_revision": 4
}
```

Success:

```json
{
  "ok": true,
  "state": "in_progress",
  "request_revision": 5
}
```

### `POST /my/sign/<int:signer_id>/submit`

Request:

```json
{
  "values": [{"field_id": 123, "value": "..."}],
  "consent": {"accepted": true, "text_hash": "<sha256>", "timezone": "UTC"},
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
  "request_revision": 5
}
```

Success:

```json
{
  "ok": true,
  "force_refresh": true,
  "redirect_url": "/my/sign/42?access_token=<token>&submitted=1",
  "request_revision": 6
}
```

Behavior:
- exact duplicate committed success for the same signer, endpoint, `idempotency_key`, and semantic payload replays the stored success envelope
- same `idempotency_key` with a different semantic payload returns `idempotency_conflict`

### `POST /my/sign/<int:signer_id>/decline`

Request:

```json
{
  "reason": "I cannot approve this document",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440001",
  "request_revision": 5
}
```

Success:

```json
{
  "ok": true,
  "force_refresh": true,
  "redirect_url": "/my/sign/42?access_token=<token>&declined=1",
  "request_revision": 6
}
```

Behavior:
- exact duplicate committed success for the same signer, endpoint, `idempotency_key`, and semantic payload replays the stored success envelope
- same `idempotency_key` with a different semantic payload returns `idempotency_conflict`

### `POST /my/sign/<int:signer_id>/otp/request`

Request:

```json
{
  "request_revision": 6
}
```

Success:

```json
{
  "ok": true,
  "force_refresh": true,
  "redirect_url": "/my/sign/42?access_token=<token>&otp_requested=1",
  "request_revision": 7
}
```

### `POST /my/sign/<int:signer_id>/otp/verify`

Request:

```json
{
  "request_revision": 7,
  "code": "123456"
}
```

Success:

```json
{
  "ok": true,
  "otp_verified": true,
  "force_refresh": true,
  "redirect_url": "/my/sign/42?access_token=<token>&otp_verified=1",
  "request_revision": 8
}
```

## Error Envelope

All mutating signer endpoints use the same error shape:

```json
{
  "ok": false,
  "error_code": "<code>",
  "message": "<human-readable>"
}
```

No additional success-only fields are returned on error responses.

## Error Codes

### Active runtime codes

- `invalid_token`
- `expired_token`
- `validation_error`
- `consent_required`
- `signing_order_blocked`
- `request_locked`
- `stale_revision`
- `idempotency_conflict`

## Current Runtime Notes

- Invalid, rotated, tampered, throttled, missing, and metadata-incomplete signer tokens return `invalid_token`.
- Revoked signer tokens return `invalid_token`.
- Exact current-token matches whose lifecycle metadata is expired return `expired_token` on signer JSONRPC routes.
- Public page/document requests with expired signer tokens still deny by redirecting to `/my`; they do not expose a separate expired-link GET UX.
- Backend copy-link surfaces now expose only currently distributable signer URLs and do not mint signer tokens on read.
- Signer completion notifications skip when no currently distributable signer URL is available.
- Explicit revoke is implemented as a manager-only pending-signer backend action; it does not introduce a new public route or response shape.
- Invalid-link throttling is enforced per signer + client IP and remains externally indistinguishable from `invalid_token`.
- Exact linked internal fallback no longer echoes stale/wrong token state into portal DOM values, document URLs, refresh URLs, or success redirects.
- Durable idempotency is implemented for `submit` and `decline` only.
- `save`, `otp/request`, and `otp/verify` do not use the durable idempotency registry yet.
- Redirect-style success envelopes for `decline`, `otp/request`, and `otp/verify` are the authoritative v1 contract.

## External Email-Only Signer Future Scope (`T310` Locked)

- The external email-only signer track reuses the same signer portal route family and the same `access_token` query/payload parameter shape.
- No email-based authentication endpoint or alternate signed-envelope URL format is planned for this track.
- External email-only signer context is intended to resolve from `signer_id + access_token`; internal authenticated fallback remains limited to signers explicitly linked by `partner_id`.
- Matching an internal user by email alone does not grant signer access.
- If a signer is explicitly linked by `partner_id`, that exact linked internal fallback still works even when a wrong/stale `access_token` is present.
- Tampered, rotated, and revoked signer tokens map to `invalid_token`.
- Expired current signer tokens now map to `expired_token` on signer JSONRPC routes only; public GET denial remains redirect-only.
- Readonly signer document access participates in the same signer+IP invalid-link throttle lifecycle as the other public signer routes, and valid token-auth success attempts a best-effort non-blocking clear of the same signer+IP throttle state. Throttled denials remain externally indistinguishable from `invalid_token`.

## Backward Compatibility

- Contract version marker: `v1`.
- Any breaking payload or envelope change requires a new documented contract version.
