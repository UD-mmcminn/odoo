# Open Sign Continuation Notes

Last updated: 2026-02-28
Scope checkpoint: T14 closed out on Odoo 19

## Why This Exists

- Build a high-quality Odoo Community signature stack so we are not blocked by Enterprise licensing.
- Produce legally defensible signing records for US-first usage (ESIGN/UETA baseline) with strong audit evidence.
- Deliver a system that looks and feels like official Odoo-quality engineering, not a thin custom patch.

## North Star Outcome

- In a dispute, we should be able to reconstruct exactly:
  - who did what
  - when they did it
  - what document/version they acted on
  - what data was entered
  - what controls were enforced at that time
- If we cannot reconstruct that story confidently, the feature is not done.

## Team Attitude For This Effort

- Treat this as legal workflow software, not just a UI feature.
- Bias toward correctness and traceability over speed.
- Be explicit about invariants and enforce them in model constraints/tests.
- Assume future maintainers may be junior; leave clear structure and breadcrumbs.
- Avoid clever shortcuts that make behavior harder to audit or explain.

## Development Trajectory (Human View)

- M1: Build a trustworthy backend core (models, constraints, state logic, ACL basics).
- M2: Add internal editor UX on top of stable backend semantics.
- M3: Expose signer experience via portal with strict token/abuse controls.
- M4: Finalize document evidence pipeline (flattened artifacts + audit package).
- M5: Add certificate-based signing as optional extension, not core dependency.
- M6: Hardening, operations, and release confidence.

## Practical Working Rules Per Session

- Start by reading `CONTINUE.md` and then `FEATURE.md` task deltas.
- Pick one coherent task slice and finish it end-to-end (code + tests + doc updates).
- When adding behavior, add tests that could fail for real regressions.
- Keep server-side rules authoritative; client-side checks are convenience only.
- If something is intentionally deferred, document where/why (task ID + risk).
- Before ending a session, update both:
  - objective status (what changed)
  - subjective context (why this change matters)

## Quality Bar For Individual Contributors

- Code should be understandable by a new contributor in one read.
- Constraints should prevent invalid legal/state outcomes, not just happy-path mistakes.
- Tests should verify denial paths, not only success paths.
- Security/compliance gaps can be deferred only when clearly tracked and non-production is explicit.
- Every meaningful design decision should be explainable in plain language.

## What Good Progress Looks Like

- Fewer assumptions hidden in heads; more decisions captured in docs/tests.
- More invariant enforcement in DB/model layer; fewer runtime surprises.
- Better failure behavior and clearer error messages for edge cases.
- Incremental milestones that can be reviewed confidently by another engineer.

## Current Status

- M0 is closed.
- M1 is open and in progress.
- `T10`, `T11`, `T12`, `T13`, `T14` are marked complete in `FEATURE.md`.
- T12 final review is complete; no additional in-scope blockers were identified.
- `T13` implementation and closeout are complete (models, ACL, views, tests, Odoo 19 compatibility fixes, deprecated-call cleanup).
- `T14` implementation and closeout are complete (request lifecycle model, version snapshot binding, transition guards, ACL + views, runtime tests green).

## What Was Implemented For T12

### Core model and wiring

- Added `open.sign.role` model:
  - `addons/open_sign/models/sign_role.py`
- Wired model import:
  - `addons/open_sign/models/__init__.py`
- Linked roles to templates:
  - `addons/open_sign/models/sign_template.py` (`role_ids`)

### Views and actions

- Added role list/search/form + template embedded assignment UI:
  - `addons/open_sign/views/sign_role_views.xml`
- Added menu entry for roles:
  - `addons/open_sign/views/sign_menus.xml`
- Added view data file to manifest:
  - `addons/open_sign/__manifest__.py`

### Security + ACL

- Added model ACL rows for users/managers/auditors:
  - `addons/open_sign/security/ir.model.access.csv`
- Record-rule matrix (`open_sign_security.xml`) is still a placeholder and deferred to `T113`.

### Tests

- Added role tests:
  - `addons/open_sign/tests/test_sign_role.py`
- Imported in:
  - `addons/open_sign/tests/__init__.py`

## Key Decisions Captured

### Participant vs signature field

- A request must have at least one participant/signer role for send flow.
- A signature field is optional (non-signature acknowledgement workflows are supported).
- This is documented in `FEATURE.md` (`R-029`, `D-010`, `CR-011`, `ADR-011`).

### Case-insensitive role-name uniqueness

- Implemented DB-backed uniqueness using normalized key:
  - `name_normalized` added to `open.sign.role`
  - SQL constraint: `UNIQUE(template_id, name_normalized)`
- Name normalization behavior:
  - Trim whitespace for display `name`
  - Store casefolded value in `name_normalized`
- This closes race-condition gaps that Python-only constraints cannot fully prevent.

## T12 Review Conclusion

- T12 is functionally complete for:
  - role model
  - assignment flows
  - role views/menu/action
  - ACL behavior tests
  - normalization/uniqueness tests
- Final review sign-off (`2026-02-27`):
  - no new T12-scope implementation blockers found
  - remaining security-scope gap remains tracked under `T113`
- Remaining deferred item:
  - `T113` record rules / multi-company scoping in `open_sign_security.xml`

## What Was Implemented For T13

### Core models and wiring

- Added `open.sign.template.field` model:
  - `addons/open_sign/models/sign_template_field.py`
- Added `open.sign.template.field.option` model:
  - `addons/open_sign/models/sign_template_field_option.py`
- Wired model imports:
  - `addons/open_sign/models/__init__.py`
- Linked template-to-field relation:
  - `addons/open_sign/models/sign_template.py` (`field_ids`)

### Constraints implemented

- `open.sign.template.field`:
  - role-template consistency (`role_id.template_id == template_id`)
  - geometry bounds (`page`, `x`, `y`, `width`, `height`)
  - sequence non-negative
  - regex validity check
  - length bounds (`min_length`, `max_length`)
  - option/type consistency (`radio` and `selection` require options; others forbid options)
- `open.sign.template.field.option`:
  - unique option value per field (`UNIQUE(field_id, value)`)
  - at most one default option per field
  - options allowed only for `radio`/`selection` field types
  - sequence non-negative

### Views and actions

- Added field list/search/form views and template embedded field editor:
  - `addons/open_sign/views/sign_template_field_views.xml`
- Added fields menu entry:
  - `addons/open_sign/views/sign_menus.xml`
- Added view data file to manifest:
  - `addons/open_sign/__manifest__.py`

### Security + ACL

- Added ACL rows for:
  - `open.sign.template.field`
  - `open.sign.template.field.option`
  - file: `addons/open_sign/security/ir.model.access.csv`
- Updated group loading for Odoo 19:
  - introduced `res.groups.privilege` and linked `res.groups` via `privilege_id`
  - file: `addons/open_sign/security/open_sign_groups.xml`

### Tests

- Added field/option tests (constraints + ACL behavior):
  - `addons/open_sign/tests/test_sign_template_field.py`
- Imported in:
  - `addons/open_sign/tests/__init__.py`
- Replaced deprecated access-check API usage in tests:
  - `check_access_rights(..., raise_exception=False)` -> `has_access(...)`
  - files: `addons/open_sign/tests/test_sign_role.py`, `addons/open_sign/tests/test_sign_template_field.py`
- Runtime verification completed:
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign --stop-after-init`
  - result: `0 failed, 0 error(s) of 24 tests`

## What Was Implemented For T14

### Core models and lifecycle engine

- Added `open.sign.request` model:
  - `addons/open_sign/models/sign_request.py`
- Added immutable template version model:
  - `addons/open_sign/models/sign_template_version.py`
- Wired model imports:
  - `addons/open_sign/models/__init__.py`
- Linked template relations:
  - `addons/open_sign/models/sign_template.py` (`version_ids`, `request_ids`)

### Lifecycle and invariant enforcement

- Added request status lifecycle:
  - `draft`, `versioned`, `sent`, `opened`, `in_progress`, `partially_signed`, `completed`, `declined`, `expired`, `cancelled`, `voided`
- Added transition guard matrix in `open.sign.request._check_transition(...)`.
- Added action methods:
  - `action_version`, `action_send`, `action_cancel`, `action_complete`, `action_void`
- Added model constraints for:
  - template-version/template consistency
  - source digest match against selected template version
  - SHA-256 format checks for source/final digests
  - completed-state requirements (`completed_at`, final attachment, final digest)
  - expiration not before sent timestamp

### Version snapshot support

- Added template snapshot helpers:
  - `open.sign.template._build_role_snapshot()`
  - `open.sign.template._build_field_snapshot()`
  - `open.sign.template.action_publish_version()`
- Added immutable template-version creation:
  - `open.sign.template.version.create_from_template(...)`
  - source PDF SHA-256 computation from attachment payload

### ACL, views, and menu

- Added ACL rows for:
  - `open.sign.request`
  - `open.sign.template.version`
  - file: `addons/open_sign/security/ir.model.access.csv`
- Added request list/search/form views and action:
  - `addons/open_sign/views/sign_request_views.xml`
- Added Requests menu entry:
  - `addons/open_sign/views/sign_menus.xml`
- Added view data file to manifest:
  - `addons/open_sign/__manifest__.py`

### Tests and runtime verification

- Added request lifecycle/constraint/ACL tests:
  - `addons/open_sign/tests/test_sign_request.py`
- Imported in:
  - `addons/open_sign/tests/__init__.py`
- Runtime verification completed:
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign --stop-after-init`
  - result: `0 failed, 0 error(s) of 31 tests`

## Important Open Risk / Follow-Up

- No current runtime blocker for `open_sign` test execution in this environment.
- `T14` intentionally does not enforce signer-presence on send yet because `open.sign.request.signer` lands in `T15`.
  - `R-029` send-gating invariant is completed in `T15` when signer rows exist.
- Remaining security-scope follow-up from earlier phases remains:
  - `T113` record rules / multi-company scoping completion in `open_sign_security.xml`

## Files Most Relevant To Resume

- `addons/open_sign/models/sign_role.py`
- `addons/open_sign/models/sign_template.py`
- `addons/open_sign/models/sign_template_field.py`
- `addons/open_sign/models/sign_template_field_option.py`
- `addons/open_sign/models/sign_template_version.py`
- `addons/open_sign/models/sign_request.py`
- `addons/open_sign/views/sign_role_views.xml`
- `addons/open_sign/views/sign_template_field_views.xml`
- `addons/open_sign/views/sign_request_views.xml`
- `addons/open_sign/views/sign_menus.xml`
- `addons/open_sign/security/ir.model.access.csv`
- `addons/open_sign/tests/test_sign_role.py`
- `addons/open_sign/tests/test_sign_template_field.py`
- `addons/open_sign/tests/test_sign_request.py`
- `FEATURE.md`

## Suggested First Steps In New Dev Environment

1. Run targeted Open Sign tests:
   - `./odoo-bin -d <db> --init open_sign --test-enable --test-tags open_sign.tests.test_sign_role --stop-after-init`
   - `./odoo-bin -d <db> --test-enable --test-tags open_sign.tests.test_sign_template_field --stop-after-init`
   - `./odoo-bin -d <db> --test-enable --test-tags open_sign.tests.test_sign_request --stop-after-init`
   - `./odoo-bin -d <db> --test-enable --test-tags /open_sign --stop-after-init`
2. If tests pass, proceed to `T15` (`open.sign.request.signer` sequencing + send gating).
3. Keep `T113` (record rules) as mandatory before any production readiness claim.

## Next Tasks (Planned Order)

1. `T15` Implement signer sequencing (`open.sign.request.signer`) with participant-required send invariants.
2. `T16` Implement `open.sign.request.value` storage and normalization.
3. `T17` Implement `open.sign.audit.log` immutable records.
4. `T113` Complete record rules and multi-company/ownership scoping before any production-readiness claim.

## Notes For Next Chat

- If the next session starts at `T15`, ensure signer model implementation completes:
  - participant-required send flow (`R-029`)
  - ordered vs parallel sequencing behavior
  - signer state transitions compatible with request status matrix (`R-006`, `R-012`)
- If the next session starts with cleanup, run runtime tests first and fix any failures before adding new features.
