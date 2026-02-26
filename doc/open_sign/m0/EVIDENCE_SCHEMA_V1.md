# Open Sign Evidence Package Schema v1

Status: Finalized for M0 (`T99`)
Date: 2026-02-26

## Versioning Policy

- Current schema version: `v1`.
- Version value is stored on requests as `evidence_schema_version`.
- Non-breaking additions keep the same major version.
- Breaking structural changes require a new schema version (`v2`, ...).

## Canonical Top-Level Structure

```json
{
  "meta": {},
  "request": {},
  "signers": [],
  "values": [],
  "audit": [],
  "artifacts": {}
}
```

## Required Sections

### `meta`

Required keys:

- `schema_version`
- `exported_at_utc`
- `exported_by`
- `generator` (module/version)

### `request`

Required keys:

- `request_id`
- `name`
- `status`
- `template_id`
- `sent_at_utc`
- `completed_at_utc` (nullable)
- `source_pdf_sha256`
- `final_pdf_sha256` (nullable until completion)

### `signers[]`

Required keys per signer:

- `signer_id`
- `role_id`
- `email`
- `state`
- `signed_at_utc` (nullable)
- `declined_reason` (nullable)
- `consent_accepted_at_utc` (nullable)
- `consent_text_hash` (nullable)

### `values[]`

Required keys per value:

- `template_field_id`
- `signer_id`
- `field_type`
- `value_text` (nullable)
- `value_json` (nullable)
- `is_valid`

### `audit[]`

Required keys per event:

- `event_sequence`
- `event_type`
- `event_at_utc`
- `hash_chain`
- `previous_hash` (nullable)
- `metadata`

### `artifacts`

Required keys:

- `source_attachment_id`
- `final_attachment_id` (nullable)
- `source_pdf_sha256`
- `final_pdf_sha256` (nullable)
- `payload_attachments` (list)

## Audit Event Taxonomy v1

Allowed event types:

- `request_created`
- `request_sent`
- `signer_opened`
- `value_saved`
- `signer_submitted`
- `signer_declined`
- `otp_requested`
- `otp_verified`
- `artifact_generated`
- `artifact_downloaded`
- `request_completed`
- `request_expired`
- `request_voided`

## Validation Rules

- `audit` entries must be ordered by `event_sequence` ascending.
- `hash_chain` continuity must be verifiable from first to last event.
- Digest fields must be 64-char lowercase hex SHA-256.
- All datetime fields are UTC values.

## Compatibility Guidance

- Exporters must always include explicit `schema_version`.
- Import/parsing tools should reject unknown major versions by default.
