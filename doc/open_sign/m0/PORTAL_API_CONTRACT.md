# Open Sign Portal API Contract (v1)

Status: Finalized for M0 (`T95`)
Date: 2026-02-26

## Conventions

- Protocol: Odoo `jsonrpc` for mutating signer operations.
- Auth: public route with signer-scoped `access_token` validation.
- Timestamp policy: server UTC is authoritative; `client_ts` is informational.
- Concurrency: mutating calls include `request_revision`; stale revisions fail.
- Idempotency: `save`, `submit`, and `decline` require `idempotency_key` (UUID format).

## Endpoints

### `POST /my/sign/<int:signer_id>/save`

Request:

```json
{
  "values": [{"field_id": 123, "value": "..."}],
  "client_ts": "2026-02-26T15:04:05Z",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440010",
  "request_revision": 4
}
```

Success:

```json
{"ok": true, "state": "in_progress", "request_revision": 5}
```

### `POST /my/sign/<int:signer_id>/submit`

Request:

```json
{
  "values": [{"field_id": 123, "value": "..."}],
  "signature_method": "draw",
  "consent": {"accepted": true, "text_hash": "<sha256>"},
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
  "request_revision": 5
}
```

Success:

```json
{"ok": true, "force_refresh": true, "redirect_url": "/my/sign/done", "request_revision": 6}
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
{"ok": true, "state": "declined", "request_revision": 6}
```

## Error Envelope

```json
{"ok": false, "error_code": "<code>", "message": "<human-readable>"}
```

## Error Codes

- `invalid_token`
- `expired_token`
- `signing_order_blocked`
- `validation_error`
- `consent_required`
- `request_locked`
- `idempotency_conflict`
- `stale_revision`

## Idempotency Policy

- Scope key by `(request_signer_id, endpoint, idempotency_key)`.
- Same key + same request hash returns stored response.
- Same key + different request hash returns `idempotency_conflict`.
- Idempotency entries have expiry and cleanup policy.

## Backward Compatibility

- Contract version marker: `v1`.
- Any breaking payload/behavior change requires `v2` endpoint contract section and migration guidance.
