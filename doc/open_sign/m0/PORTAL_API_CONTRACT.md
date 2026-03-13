# Open Sign Portal API Contract (v1)

Status: Finalized for M0 (`T95`), runtime-locked in `T38`
Date: 2026-03-13

## Conventions

- Protocol: Odoo `jsonrpc` for mutating signer operations.
- Auth: signer-scoped public token or the approved authenticated internal signer fallback where the route currently allows it.
- Timestamp policy: server UTC is authoritative.
- Concurrency: mutating calls include `request_revision`; stale revisions fail.
- Idempotency: `save`, `submit`, and `decline` currently validate `idempotency_key` format only. Durable idempotency conflict semantics remain deferred to `T316` / `T317`.

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
- `validation_error`
- `consent_required`
- `signing_order_blocked`
- `request_locked`
- `stale_revision`

### Reserved / deferred codes

- `expired_token`
- `idempotency_conflict`

## Current Runtime Notes

- Invalid or rotated signer tokens currently return `invalid_token`.
- True token-expiry behavior is not implemented yet.
- Durable idempotency conflict / replayed-response semantics are not implemented yet.
- Redirect-style success envelopes for `decline`, `otp/request`, and `otp/verify` are the authoritative v1 contract.

## Backward Compatibility

- Contract version marker: `v1`.
- Any breaking payload or envelope change requires a new documented contract version.
