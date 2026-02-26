# Open Sign Observability Baseline Proposal (v1)

Status: Finalized (`T08`)
Date: 2026-02-26

## Goal
Define minimum telemetry for legal-signature reliability, security, and auditability.

## Event Logging (Structured)

Mandatory audit events:
- `value_saved` (field update)
- `signer_submitted` (signature applied + submit)
- `signer_declined`
- `request_versioned`
- `request_sent`
- `request_completed`
- `artifact_generated`
- `artifact_downloaded`
- `idempotency_conflict`
- `stale_revision_rejected`
- `token_validation_failed`

Required event attributes:
- `request_id`, `signer_id` (when applicable), `event_type`, `event_at_utc`
- actor context (`user_id` or portal signer id)
- request status before/after (for transition events)
- endpoint and idempotency key (for mutating portal calls)
- `ip`, `user_agent` for signer-facing events

## Metrics

### Reliability
- `open_sign.portal.submit.success.count`
- `open_sign.portal.submit.error.count`
- `open_sign.portal.save.success.count`
- `open_sign.portal.decline.success.count`
- `open_sign.request.completed.count`
- `open_sign.request.declined.count`
- `open_sign.request.expired.count`

### Security / Abuse
- `open_sign.portal.token.invalid.count`
- `open_sign.portal.token.expired.count`
- `open_sign.portal.idempotency.conflict.count`
- `open_sign.portal.replay.blocked.count`
- `open_sign.portal.otp.failed.count` (if OTP enabled)

### Performance
- `open_sign.portal.submit.latency.ms` (p50/p95/p99)
- `open_sign.portal.save.latency.ms` (p50/p95/p99)
- `open_sign.pdf.finalize.latency.ms` (p50/p95/p99)
- `open_sign.evidence.export.latency.ms` (p50/p95/p99)

### Data Integrity
- `open_sign.digest.mismatch.count`
- `open_sign.audit.hash_chain.verify.fail.count`
- `open_sign.request.without_version.blocked.count`

## Alerts (Initial Thresholds)

- High error rate:
  - Trigger when `submit.error / submit.total > 5%` for 10 minutes.
- Token abuse spike:
  - Trigger when invalid/expired token failures exceed 50 in 10 minutes.
- Idempotency/race anomaly:
  - Trigger when `idempotency.conflict.count > 20` in 10 minutes.
- PDF pipeline degradation:
  - Trigger when `pdf.finalize p95 > 5s` for 15 minutes.
- Integrity breach:
  - Trigger on any digest mismatch or hash-chain verification failure.

## Dashboard Panels

1. Request lifecycle funnel: `draft -> versioned -> sent -> completed/declined/expired`
2. Portal endpoint health: success/error and latency by endpoint
3. Security anomalies: token failures, replay blocks, idempotency conflicts
4. Evidence integrity: digest/hash-chain verification outcomes

## Retention For Telemetry

- Operational metrics: 90 days minimum.
- Security event logs: 1 year minimum.
- Audit events tied to legal evidence: retained with request retention policy.

## Approval Checklist

- [x] Metric names and dimensions approved.
- [x] Alert thresholds approved.
- [x] Dashboard panel set approved.
- [x] Ownership/on-call routing approved.
