# Open Sign Merge Gate Policy Proposal (v1)

Status: Finalized (`T09`)
Date: 2026-02-26

## Goal
Define mandatory PR checks so Open Sign changes meet Odoo-quality and legal-evidence expectations.

## What Is A Merge Gate?
A merge gate is a required check that must pass before a PR can be merged.

## Required Merge Gates

1. Lint and Odoo structure conformance
- `test_lint` subset for manifests, naming, imports, signatures, i18n, indexes
- No missing `__init__.py` in module/test packages

2. Module upgrade safety
- `./odoo-bin -d <db_name> -u <touched_modules> --stop-after-init`
- Must pass for all touched Open Sign modules

3. Backend test coverage
- `open_sign` and `open_sign_portal` tagged tests must pass
- Any changed model/controller must have updated tests

4. Portal security gates
- Replay/expiry/token tests pass
- Idempotency and stale revision tests pass for mutating endpoints

5. Schema/migration gate (when model fields/constraints/data XML change)
- Migration scripts present/updated
- Upgrade + regression tests pass
- Schema contract section in `FEATURE.md` updated

6. Contract compatibility gate (when portal API changes)
- `PORTAL_API_CONTRACT.md` updated
- Error codes and payload contract tests updated

7. Evidence integrity gate (when PDF/evidence logic changes)
- Digest generation/verification tests pass
- Audit hash-chain tests pass

## PR Checklist Mapping

Every Open Sign PR must include:
- Task IDs (`T*`) and requirement links (`R*`)
- Test evidence for affected gate categories
- For feature branches: `FEATURE.md` task/update-log changes
- For non-feature branches: reference task card/issue link and include impacted gate evidence

## Suggested CI Job Layout

- `open_sign_lint`
- `open_sign_upgrade`
- `open_sign_tests_backend`
- `open_sign_tests_portal_security`
- `open_sign_tests_web`
- `open_sign_tests_evidence_integrity`

## Blocker Rules

- Any required gate failure blocks merge.
- Security/integrity gate failures require owner approval from Security or Backend lead.

## Approval Checklist

- [x] Required gates approved.
- [x] CI job mapping approved.
- [x] Blocker and exception policy approved.
