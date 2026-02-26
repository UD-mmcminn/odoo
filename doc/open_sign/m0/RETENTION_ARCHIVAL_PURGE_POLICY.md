# Open Sign Retention, Archival, and Purge Policy (v1)

Status: Finalized (`T07`)
Date: 2026-02-26

## Policy Principles

- Retention must be configurable by document class/policy profile.
- Default retention is indefinite (no automatic expiration).
- Purge is configurable but can only run after retention requirement is satisfied.
- Legal hold always overrides purge operations.

## Data Classes In Scope

- Requests, signer/value records, audit logs
- Source and final PDF artifacts
- Evidence package exports
- Optional certificate logs

## Effective Rules

1. Retention window
- Each request class has `retention_until` derived from policy.
- Default policy sets `retention_until = null` (retain forever).

2. Purge eligibility
- Purge eligibility timestamp (`purge_eligible_at`) must be >= `retention_until`.
- If retention is indefinite, purge is never auto-eligible.

3. Example
- Retention: 7 years
- Purge eligibility: 10 years
- Behavior: 3-year non-required retention buffer before purge eligibility

4. Legal hold
- `legal_hold = true` blocks purge regardless of timestamps.
- Legal hold changes are audited with actor/time/reason.

## Operational Controls

- Purge runs in dry-run mode first and reports candidate counts.
- Destructive purge requires explicit privileged execution path.
- Purge actions emit audit events and summary reports.

## Minimum Tests

- Retention date computation tests
- Purge eligibility boundary tests
- Legal hold override tests
- Dry-run reporting tests
