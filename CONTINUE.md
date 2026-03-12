# Open Sign Continuation Notes

Last updated: 2026-03-12
Scope checkpoint: T36 portal replay/token-abuse hardening closed on Odoo 19

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
- Follow `AGENTS.md` workflow guardrails for every coding session.
- Pick one coherent task slice and finish it end-to-end (code + tests + doc updates).
- Every code-change session must end with a comprehensive post-change review (scope intent, diff correctness, cross-model impact, security/authority boundaries, and regression checks).
- Run `scripts/review_gate_open_sign.sh` (or document why a step is deferred) before marking a task complete.
- Execute `REVIEW_CHECKLIST.md` line-by-line during closeout.
- When adding behavior, add tests that could fail for real regressions.
- Keep server-side rules authoritative; client-side checks are convenience only.
- If something is intentionally deferred, document where/why (task ID + risk).
- Before ending a session, update both:
  - objective status (what changed)
  - subjective context (why this change matters)

## Task Closeout Hardening Checklist (Mandatory)

Use this before marking any task complete (especially model/state/security work):

- Perform a deliberate end-of-change review against the task contract and the actual diff; do not rely on in-flight assumptions made while coding.
- Define server-authoritative fields and block direct client/user mutation in model `create`/`write` where needed.
- Add explicit action precondition guards (not only structural presence checks).
- Add denial-path tests for abuse/tamper attempts and invalid state transitions.
- Ensure UI `readonly`/visibility aligns with server authority (UI must not expose forbidden writes).
- Verify ACL expectations with tests for user/manager/auditor behavior.
- Validate invariants at DB/model layer (SQL constraints and Python constraints) rather than relying on client behavior.
- Re-run task test scope and confirm no regression in adjacent flows.
- Record review-gate results (`scripts/review_gate_open_sign.sh`) in closeout notes.
- If any guard is intentionally deferred, log task ID + risk + owner in `FEATURE.md`/`CONTINUE.md`.
- Re-run this checklist as a recurring re-audit after each major phase slice and after every 3 completed implementation tasks.

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
- M1 is closed.
- M2 implementation tasks are complete (`T20`-`T26`); milestone sign-off/demo review is next.
- `T10`, `T11`, `T12`, `T13`, `T14`, `T15`, `T16`, `T17`, `T18`, `T19`, `T110`, `T111`, `T112`, `T113` are marked complete in `FEATURE.md`.
- `T20` implementation is complete (new `open_sign_web` addon scaffold, manifest asset wiring, initial JS/XML/SCSS skeleton, and baseline frontend test stubs).
- `T21` implementation is complete (Template Canvas OWL action with drag/move/resize interactions, editor action/menu wiring, and runtime validation).
- `T21` follow-up hardening is complete: `open_sign_web` Editor menu visibility is now restricted to `open_sign.group_open_sign_user` (auditor access removed).
- `T22` implementation and closeout are complete (field palette + property editor with typed insertion and client-side property normalization in `open_sign_web`; module load and `/open_sign` regression remain green).
- `T22` hardening follow-up is complete: field-palette labels are now JS-translatable, unknown field types now fallback deterministically to `text`, and backend-safe payload serialization is now wired through `serializeTemplateFieldsForBackend()` + `toTemplateFieldVals()` (with editor-only properties kept client-side and excluded from backend payloads).
- `T23` implementation and closeout are complete (template-aware signer role assignment in editor via template/role selectors, role normalization across template changes, and backend payload mapping via `role_id`), with `/open_sign` regression green and `/open_sign_web` runtime load validated.
- `T23` hardening follow-up is complete: removed silent role reassignment on template switch, removed misleading `Unassigned` role UI path, blocked new-field creation when template roles are absent, added stale async response protection for role loading, and added role-validity utility test coverage.
- `T24` implementation and closeout are complete (client-side value normalization/validation matrix in `signing_form.js` aligned to backend validation service for field types, required/optional semantics, option canonicalization, regex/length checks, and signature payload attachment rules); `/open_sign` regression is green and `/open_sign_web` runtime load is green.
- `T25` implementation and closeout are complete (signature adoption dialog using Odoo `NameAndSignature`, method normalization for draw/type/upload, client-side adoption payload validation, and editor integration from field properties for `signature`/`stamp` fields).
- `T25` hardening follow-up is complete: adopted signature/stamp payloads now create `ir.attachment` rows and persist `signed_payload_attachment_id` in the adopted payload contract, aligned with backend signature value requirements.
- `T26` implementation and closeout are complete (explicit frontend test-runner wiring in `open_sign_web/tests/test_js.py`, scoped HOOT tagging for addon tests, expanded geometry/validation payload edge-case coverage, and frontend discovery now non-zero under `/open_sign_web` after module install/upgrade).
- T12 final review is complete; no additional in-scope blockers were identified.
- `T13` implementation and closeout are complete (models, ACL, views, tests, Odoo 19 compatibility fixes, deprecated-call cleanup).
- `T14` implementation and closeout are complete (request lifecycle model, version snapshot binding, transition guards, ACL + views, runtime tests green).
- `T15` implementation and closeout are complete (request signer model, sequence helpers, participant-required send gating, signer ACL + request form integration, runtime tests green).
- `T15` post-review hardening is applied: non-superuser lifecycle/evidence signer writes are blocked, send now requires actionable signer(s), signer lifecycle fields are readonly in request form, and regression tests cover these guards.
- `T16` implementation and closeout are complete (request value model, cross-model invariants, value normalization baselines, server-authoritative `is_valid` guard, value ACL matrix, runtime tests green).
- `T16` post-review hardening is applied: `default_*` context bypass is blocked for value validation/lifecycle-sensitive fields, context-provided defaults are normalized through server logic, and regression tests cover this path.
- `T17` implementation and closeout are complete (audit log model, event taxonomy selection, request-local sequence/hash uniqueness, append-only immutability guards, read-only ACLs, and dedicated tests).
- `T18` implementation and closeout are complete (centralized field validation service, request value required/optional and rule validation, signer evidence-field format validation, and expanded regression coverage).
- `T19` implementation and closeout are complete (base backend navigation, list/form/kanban coverage across core models, standalone backend views for version/signer/value/audit models, and backend-view regression tests).
- `T18`/`T19` post-review hardening is applied: non-superuser signer/value create/write/unlink mutations are now blocked when request status is terminal (`completed`, `cancelled`, `voided`), with dedicated denial-path regression tests.
- `T110` implementation and closeout are complete (schema-hardening SQL checks/FK/index updates plus pre-validation guards to keep deterministic model-level errors); full `/open_sign` suite is green.
- `T111` implementation and closeout are complete (scheduled actions + reminder/expiration cron handlers + dedicated cron tests); full `/open_sign` suite is green.
- `T112` implementation and closeout are complete (upgrade scripts in `upgrades/1.1`, addon version bump to `1.1`, migration-time data normalization for new schema constraints); full `/open_sign` suite is green.
- `T118` (`FEATURE.md` `T610`) recurring hardening re-audit is complete with no new blocking findings; server-authority controls, denial paths, ACL/rule expectations, and UI/server alignment remain intact across completed M1 scope.
- `T30` implementation and closeout are complete (new `open_sign_portal` addon scaffold with controller route shells, portal templates, model helper, security placeholders, and dedicated scaffold tests), with `/open_sign_portal` and `/open_sign` regression green.
- `T31` implementation and closeout are complete (`open.sign.request.signer` now inherits `portal.mixin` with standard tokenized access URL flow, controller access checks now use `CustomerPortal._document_check_access`, and portal-token visibility is restricted away from auditor-only roles), with `/open_sign_portal` and `/open_sign` regression green.
- `T33` implementation and closeout are complete (ordered-signing portal policy/UX hardening): sequential out-of-turn signers now get a read-only waiting page with refresh-to-unlock behavior, `save` and `submit` now both return `signing_order_blocked` when out of turn, waiting-page visits do not create signer-open evidence, same-sequence signers remain actionable together, and parallel requests explicitly allow mutable signers to open/save/submit immediately.
- `T33` post-review hardening is applied: signer contract fields (`request_id`, `partner_id`, `email`, `role_id`, `sequence`) now freeze for non-superusers once a request reaches `versioned`, portal `save`/`submit` re-check mutable-state and order under request lock so `stale_revision` beats `signing_order_blocked`, waiting-page assertions now verify the actual disabled signer control, and full `/open_sign`, `/open_sign_portal`, and `scripts/review_gate_open_sign.sh --skip-web` validation are green.

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
- Record-rule matrix (`open_sign_security.xml`) was a placeholder during T12 and is now implemented in `T113` (2026-02-28).

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
  - security-scope gap that was tracked under `T113` is now closed (`2026-02-28`)

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

## What Was Implemented For T15

### Core model and request integration

- Added `open.sign.request.signer` model:
  - `addons/open_sign/models/sign_request_signer.py`
- Wired model imports:
  - `addons/open_sign/models/__init__.py`
- Linked signer relation to requests:
  - `addons/open_sign/models/sign_request.py` (`signer_ids`)

### Sequencing and send-gating logic

- Added sequence-oriented signer helper on requests:
  - `open.sign.request._get_actionable_signers()`
  - supports ordered mode (lowest pending/opened sequence) and parallel mode (all pending/opened).
- Added participant-required send invariant:
  - `open.sign.request.action_send()` now rejects send when no signer rows exist (`R-029`).
- Added signer-state counters (computed, stored):
  - `signed_count`, `pending_count`, `declined_count` now compute from signer states.

### Signer model constraints

- Unique signer role per request:
  - `UNIQUE(request_id, role_id)`
- `role_id.template_id` must match `request_id.template_id`.
- `state='signed'` requires `signed_at`.
- `sequence >= 0`.
- Email normalization/validation via server-side sanitization.

### ACL and request form UX

- Added ACL rows for `open.sign.request.signer` (user/manager/auditor):
  - `addons/open_sign/security/ir.model.access.csv`
- Added signer editor section in request form:
  - `addons/open_sign/views/sign_request_views.xml`

### Tests and runtime verification

- Extended request tests to cover signer model, send gating, sequence helper behavior, counters, and signer ACL:
  - `addons/open_sign/tests/test_sign_request.py`
- Runtime verification completed:
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign --stop-after-init`
  - result: `0 failed, 0 error(s) of 40 tests`

## What Was Implemented For T16

### Core model and wiring

- Added `open.sign.request.value` model:
  - `addons/open_sign/models/sign_request_value.py`
- Wired model imports:
  - `addons/open_sign/models/__init__.py`
- Linked values to requests/signers/template fields:
  - `addons/open_sign/models/sign_request.py` (`value_ids`)
  - `addons/open_sign/models/sign_request_signer.py` (`value_ids`)
  - `addons/open_sign/models/sign_template_field.py` (`request_value_ids`)

### Storage constraints and normalization

- Added unique value slot constraint:
  - `UNIQUE(request_id, template_field_id, signer_id)`
- Enforced cross-model integrity:
  - `template_field_id.template_id == request_id.template_id`
  - `signer_id.request_id == request_id`
  - `signer_id.role_id == template_field_id.role_id`
- Added baseline server normalization by field type:
  - `value_text`: trim/email lowercase/initials uppercase/multiline newline normalization/selection-radio canonical option key mapping.
  - `value_json`: checkbox bool normalization, date ISO payload normalization, strikethrough boolean-shape normalization.

### Server-authoritative validation state

- Added model-layer guard so non-superusers cannot set/modify `is_valid` directly.
- Added denial-path tests covering attempted `is_valid` tampering.

### ACL and tests

- Added ACL rows for `open.sign.request.value` (user/manager/auditor):
  - `addons/open_sign/security/ir.model.access.csv`
- Added dedicated request value tests:
  - `addons/open_sign/tests/test_sign_request_value.py`
- Imported in:
  - `addons/open_sign/tests/__init__.py`
- Runtime verification completed:
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign --stop-after-init`
  - result: `0 failed, 0 error(s) of 48 tests`

## What Was Implemented For T17

### Core model and wiring

- Added `open.sign.audit.log` model:
  - `addons/open_sign/models/sign_audit_log.py`
- Wired model import:
  - `addons/open_sign/models/__init__.py`
- Linked request relation:
  - `addons/open_sign/models/sign_request.py` (`audit_log_ids`)

### Audit invariants and immutability

- Added `AuditEventType` selection contract from schema/taxonomy.
- Added request-local uniqueness constraints:
  - `UNIQUE(request_id, hash_chain)`
  - `UNIQUE(request_id, event_sequence)`
- Added model checks for:
  - hash fields (`hash_chain`, `previous_hash`, `consent_text_hash`) as lowercase SHA-256 hex when set
  - signer/request consistency (`signer_id.request_id == request_id`)
  - positive event sequence (`event_sequence > 0`)
- Added append-only/immutability guard behavior:
  - direct `write`/`unlink` blocked by default
  - terminal requests (`completed`/`voided`) return explicit immutable error
  - privileged repair path allowed only via superuser + context `open_sign_allow_audit_log_repair`

### ACL and tests

- Added ACL rows for `open.sign.audit.log` (user/manager/auditor read-only):
  - `addons/open_sign/security/ir.model.access.csv`
- Added dedicated audit log tests:
  - `addons/open_sign/tests/test_sign_audit_log.py`
- Imported in:
  - `addons/open_sign/tests/__init__.py`
- Runtime verification completed:
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign --stop-after-init --http-port=8073`
  - result: `0 failed, 0 error(s) of 54 tests`

## What Was Implemented For T18

### Validation service and value-model wiring

- Added centralized validation service package:
  - `addons/open_sign/services/__init__.py`
  - `addons/open_sign/services/validation_service.py`
- Wired request-value normalization/validation through the service:
  - `addons/open_sign/models/sign_request_value.py`
- Added server-authoritative enforcement for:
  - required vs optional field behavior (`template_field.required`)
  - field-type-specific normalization/validation (`text`, `multiline`, `email`, `phone`, `initials`, `checkbox`, `radio`, `selection`, `date`, `strikethrough`, `signature`, `stamp`)
  - template-field regex and length rules
  - required attachment on `signature`/`stamp` payload values

### Signer evidence-field format validation

- Added signer evidence format checks/sanitization in:
  - `addons/open_sign/models/sign_request_signer.py`
- Covered fields:
  - `ip_last` must be valid IPv4/IPv6
  - `consent_text_hash` must be lowercase SHA-256 hex
  - `signer_timezone` must be valid IANA timezone

### Tests and runtime verification

- Extended value validation tests:
  - `addons/open_sign/tests/test_sign_request_value.py`
- Extended signer evidence-format tests:
  - `addons/open_sign/tests/test_sign_request.py`
- Runtime verification completed:
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign/tests/test_sign_request.py --stop-after-init --http-port=8076`
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign/tests/test_sign_request_value.py --stop-after-init --http-port=8077`
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign --stop-after-init --http-port=8078`
  - result: `0 failed, 0 error(s) of 56 tests`

## What Was Implemented For T19

### Backend views/actions

- Added `kanban` views and `list,kanban,form` action modes for:
  - templates (`addons/open_sign/views/sign_template_views.xml`)
  - requests (`addons/open_sign/views/sign_request_views.xml`)
  - roles (`addons/open_sign/views/sign_role_views.xml`)
  - template fields (`addons/open_sign/views/sign_template_field_views.xml`)
- Added standalone list/search/form/kanban view files + actions for:
  - template versions (`addons/open_sign/views/sign_template_version_views.xml`)
  - request signers (`addons/open_sign/views/sign_request_signer_views.xml`)
  - request values (`addons/open_sign/views/sign_request_value_views.xml`)
  - audit logs (`addons/open_sign/views/sign_audit_log_views.xml`)
- Updated manifest data loading for new view files:
  - `addons/open_sign/__manifest__.py`

### Menu/navigation coverage

- Expanded root Open Sign navigation for operations:
  - `Requests`, `Templates`, `Signers`, `Values`, `Audit Logs`
- Added `Configuration` subtree:
  - `Roles`, `Fields`, `Template Versions`
- File:
  - `addons/open_sign/views/sign_menus.xml`

### Request form coverage

- Added request-form notebook pages for:
  - captured values (`value_ids`)
  - request audit timeline (`audit_log_ids`)
- File:
  - `addons/open_sign/views/sign_request_views.xml`

### Tests and runtime verification

- Added backend-view regression tests (actions include kanban mode, kanban arches load, menu wiring, auditor audit-read visibility):
  - `addons/open_sign/tests/test_sign_backend_views.py`
- Imported in:
  - `addons/open_sign/tests/__init__.py`
- Runtime verification completed:
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign/tests/test_sign_backend_views.py --stop-after-init --http-port=8079`
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign --stop-after-init --http-port=8080`
  - result: `0 failed, 0 error(s) of 59 tests`

### Post-review hardening updates

- Added terminal-request mutation guards in:
  - `addons/open_sign/models/sign_request_signer.py`
  - `addons/open_sign/models/sign_request_value.py`
- Guard behavior:
  - non-superusers cannot create/write/unlink signer or value records when `request.status in ('completed', 'cancelled', 'voided')`
- Added dedicated denial-path tests:
  - `test_signer_mutation_blocked_on_terminal_requests` in `addons/open_sign/tests/test_sign_request.py`
  - `test_value_mutation_blocked_on_terminal_requests` in `addons/open_sign/tests/test_sign_request_value.py`
- Runtime verification completed:
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign/tests/test_sign_request.py --stop-after-init --http-port=8084`
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign/tests/test_sign_request_value.py --stop-after-init --http-port=8085`
  - `./odoo-bin -d test_open_sign -u open_sign --test-enable --test-tags /open_sign --stop-after-init --http-port=8086`
  - result: `0 failed, 0 error(s) of 61 tests`
- Extended hardening follow-up:
  - request immutability now treats `completed`, `cancelled`, and `voided` as immutable for non-superusers:
    - `addons/open_sign/models/sign_request.py`
  - request `unlink` remains retention-first (soft delete via `active=False` + `deleted_at`) and preserves linked signer/value/audit evidence rows.
  - request value multi-record `write` now uses prepared per-record payloads + savepointed all-or-nothing apply to prevent partial success when validation fails mid-batch:
    - `addons/open_sign/models/sign_request_value.py`
  - terminal guard tests now cover all terminal statuses (`completed`, `cancelled`, `voided`) for signer/value mutation denial paths:
    - `addons/open_sign/tests/test_sign_request.py`
    - `addons/open_sign/tests/test_sign_request_value.py`
  - added atomicity regression test for multi-record value write rollback:
    - `test_multi_record_write_rolls_back_on_validation_error` in `addons/open_sign/tests/test_sign_request_value.py`
  - runtime verification completed:
    - `./odoo-bin -d test_open_sign_t19_run2 -i open_sign --test-enable --test-tags open_sign --stop-after-init --http-port=8095`
    - result: `0 failed, 0 error(s) of 63 tests`

## What Was Implemented For T113

- Implemented full `open_sign` record-rule matrix in:
  - `addons/open_sign/security/open_sign_security.xml`
- Rule coverage now includes:
  - company isolation for templates, template versions, roles, template fields, field options, requests, signers, values, and audit logs
  - owner/assignee scoping for user-group access on request-linked models (`open.sign.request`, `open.sign.request.signer`, `open.sign.request.value`, `open.sign.audit.log`)
  - manager/auditor company-scoped visibility aligned to allowed companies
- Added dedicated security regression tests:
  - `addons/open_sign/tests/test_sign_security_rules.py`
- Updated test imports:
  - `addons/open_sign/tests/__init__.py`
- Updated ACL test fixtures to align with owner/assignee rule semantics:
  - `addons/open_sign/tests/test_sign_request.py`
  - `addons/open_sign/tests/test_sign_request_value.py`
- Runtime verification completed:
  - `./odoo-bin -d test_open_sign_t113 -i open_sign --test-enable --test-tags /open_sign/tests/test_sign_security_rules.py --stop-after-init --http-port=8100`
  - `./odoo-bin -d test_open_sign_t113_fix2 -i open_sign --test-enable --test-tags /open_sign/tests/test_sign_request.py,/open_sign/tests/test_sign_request_value.py --stop-after-init --http-port=8103`
  - `./odoo-bin -d test_open_sign_t113_full2 -i open_sign --test-enable --test-tags /open_sign --stop-after-init --http-port=8104`
  - result: `0 failed, 0 error(s)` including full `/open_sign` run (`69` tests)

## Important Open Risk / Follow-Up

- No current runtime blocker for `open_sign` test execution in this environment.
- `T113` security-scope follow-up is now completed and validated with dedicated multi-company/ownership tests.
- `T20` module install is validated and backend regression remains green (`/open_sign`: `0 failed, 0 errors`, `74` tests).
- `T21` module install is validated and backend regression remains green (`/open_sign`: `0 failed, 0 errors`, `74` tests).
- `T22` module install is validated and backend regression remains green (`/open_sign`: `0 failed, 0 errors`, `74` tests).
- Remaining follow-up for the just-closed M1 scope:
  - monitor reminder cadence behavior in real environments and tune via `open_sign.reminder_interval_hours`
  - maintain upgrade-script CI coverage so `T112` remains effective across future schema changes
- M2 test-runner note:
  - `/open_sign_web` now executes non-zero post-tests after explicit module install/upgrade (`-i/-u open_sign_web`) with `open_sign_web/tests/test_js.py`.
  - In this local environment, the HOOT browser run is skipped because `websocket-client` is missing; asset-registration and backend regression checks still pass.

## Deferred Queue (Tracked Next-Up)

- `DQ-002` (`T43`): audit hash-chain continuity checks remain deferred to service-level implementation.

## Files Most Relevant To Resume

- `addons/open_sign/models/sign_role.py`
- `addons/open_sign/models/sign_template.py`
- `addons/open_sign/models/sign_template_field.py`
- `addons/open_sign/models/sign_template_field_option.py`
- `addons/open_sign/models/sign_template_version.py`
- `addons/open_sign/models/sign_request.py`
- `addons/open_sign/models/sign_request_signer.py`
- `addons/open_sign/models/sign_request_value.py`
- `addons/open_sign/models/sign_audit_log.py`
- `addons/open_sign/services/validation_service.py`
- `addons/open_sign/views/sign_role_views.xml`
- `addons/open_sign/views/sign_template_field_views.xml`
- `addons/open_sign/views/sign_request_views.xml`
- `addons/open_sign/views/sign_template_version_views.xml`
- `addons/open_sign/views/sign_request_signer_views.xml`
- `addons/open_sign/views/sign_request_value_views.xml`
- `addons/open_sign/views/sign_audit_log_views.xml`
- `addons/open_sign/views/sign_menus.xml`
- `addons/open_sign/security/ir.model.access.csv`
- `addons/open_sign/__manifest__.py`
- `addons/open_sign_web/__manifest__.py`
- `addons/open_sign_web/static/src/js/field_palette.js`
- `addons/open_sign_web/static/src/js/field_properties_panel.js`
- `addons/open_sign_web/static/src/js/template_canvas.js`
- `addons/open_sign_web/static/src/xml/field_properties_panel.xml`
- `addons/open_sign_web/static/src/xml/template_canvas.xml`
- `addons/open_sign_web/static/src/scss/open_sign.scss`
- `addons/open_sign_web/views/open_sign_web_menu.xml`
- `addons/open_sign_web/static/src/js/signing_form.js`
- `addons/open_sign_web/static/tests/test_field_palette.test.js`
- `addons/open_sign_web/static/tests/test_field_properties_panel.test.js`
- `addons/open_sign_web/static/tests/test_template_canvas.test.js`
- `addons/open_sign_web/static/tests/test_signing_form.test.js`
- `addons/open_sign_web/static/tests/test_coordinate_normalization.test.js`
- `addons/open_sign_web/tests/__init__.py`
- `addons/open_sign_web/tests/test_js.py`
- `addons/open_sign/data/ir_cron.xml`
- `addons/open_sign/upgrades/1.1/pre-migrate.py`
- `addons/open_sign/upgrades/1.1/post-migrate.py`
- `addons/open_sign/tests/test_sign_role.py`
- `addons/open_sign/tests/test_sign_template_field.py`
- `addons/open_sign/tests/test_sign_request.py`
- `addons/open_sign/tests/test_sign_request_value.py`
- `addons/open_sign/tests/test_sign_audit_log.py`
- `addons/open_sign/tests/test_sign_cron.py`
- `addons/open_sign/tests/test_sign_backend_views.py`
- `FEATURE.md`

## Suggested First Steps In New Dev Environment

1. Run targeted Open Sign tests:
   - `./odoo-bin -d <db> --init open_sign --test-enable --test-tags /open_sign/tests/test_sign_role.py --stop-after-init`
   - `./odoo-bin -d <db> --test-enable --test-tags /open_sign/tests/test_sign_template_field.py --stop-after-init`
   - `./odoo-bin -d <db> --test-enable --test-tags /open_sign/tests/test_sign_request.py --stop-after-init`
   - `./odoo-bin -d <db> --test-enable --test-tags /open_sign/tests/test_sign_request_value.py --stop-after-init`
   - `./odoo-bin -d <db> --test-enable --test-tags /open_sign/tests/test_sign_audit_log.py --stop-after-init`
   - `./odoo-bin -d <db> --test-enable --test-tags /open_sign/tests/test_sign_security_rules.py --stop-after-init`
   - `./odoo-bin -d <db> --test-enable --test-tags /open_sign --stop-after-init`
   - `./odoo-bin -d <db> -u open_sign_web --test-enable --test-tags /open_sign_web --stop-after-init`
   - `./odoo-bin -d <db> -i open_sign_portal --stop-after-init`
   - `./odoo-bin -d <db> --test-enable --test-tags /open_sign_portal --stop-after-init`
   - `scripts/review_gate_open_sign.sh --skip-web -d <db>`
2. If tests pass, continue Phase 3 with `T37` optional OTP verification flow on top of the now-closed `T32`/`T33`/`T34`/`T35`/`T36` portal baseline.
3. Re-run recurring hardening re-audit (`T610`) after each major phase slice and after every 3 completed implementation tasks.

## Next Tasks (Planned Order)

1. `T37` Implement optional OTP verification flow.

## Notes For Next Chat

- `T32` is closed. The portal session implementation now includes:
  - separate internal preview route (`/my/sign/<id>/preview`) with no signer evidence mutation
  - signer-only session open/save/submit auth on real signer routes
  - real signer read-only review for `completed`, `declined`, and `expired` requests, while mutation remains limited to `sent`, `opened`, `in_progress`, and `partially_signed`
  - internal preview intentionally supports historical review for `versioned`, active signer-session states, and `completed`/`declined`/`expired`
  - `cancelled` and `voided` remain denied on signer, preview, and tokenized document routes
  - save/submit savepoints with rollback-safe lock/revision handling
  - request-version snapshot-backed portal rendering/validation, including legacy snapshot fallback and fail-closed contract errors
  - unsupported portal fields excluded from serialization so existing stored values are preserved
  - active-request field role/delete guards to prevent live template drift from breaking in-flight contracts
  - tokenized document access aligned with read-only review states and still serving the source PDF until `T40`/`T41`
  - explicit regression coverage proving terminal preview remains non-mutating and scaffold action endpoints stay immutable on terminal requests
- `T33` is now closed. Additional portal ordering guarantees now include:
  - sequential out-of-turn signers render as read-only waiting sessions instead of failing only at submit time
  - sequential out-of-turn `save` and `submit` both return `signing_order_blocked`
  - waiting-page visits do not stamp `signer_opened`, `last_opened_at`, `ip_last`, or request revision
  - same-sequence signers remain actionable together and parallel requests explicitly allow all mutable signers to open/save/submit
  - signer contract fields (`request_id`, `partner_id`, `email`, `role_id`, `sequence`) are frozen for non-superusers from `versioned` onward so ordered-signing no longer depends on mutable active signer rows
  - portal ordering is re-evaluated under request lock during `save` and `submit`, so `stale_revision` wins over `signing_order_blocked`
- `T34` is now closed. Additional portal decline guarantees now include:
  - authorized signers can decline through the real signer session with a required normalized reason via `POST /my/sign/<id>/decline`
  - sequential out-of-turn signers may decline from the waiting page even though `save` and `submit` remain order-blocked
  - successful decline sets only the acting signer to `declined`, stores `declined_reason`, updates `ip_last`, and transitions the request to `declined` without mass-overwriting other signer states
  - each successful decline appends exactly one `signer_declined` audit event with reason and pre-transition request/signer state metadata
  - waiting-page decline remains non-opening evidence: it does not stamp `signer_opened` or `last_opened_at`
  - post-decline signer review uses the existing readonly terminal-review contract, shows a success flash, and exposes the decliner's own reason block without leaking it to other signers
- `T35` is now closed. Additional notification and resend guarantees now include:
  - initial send queues invitation mail for the current actionable signer wave only and rolls back the send transition if any actionable invitation cannot be queued
  - reminder cron queues reminders for actionable signers only and updates reminder counters only when at least one reminder is successfully queued
  - request completion now appends `request_completed` and best-effort queues owner + signer completion notifications with the final attachment
  - portal submit now best-effort queues invitation mail for newly actionable next-wave pending signers without rolling back the signer submit on queue failure
  - portal decline now best-effort queues an owner-only decline notification without rolling back the decline action on queue failure
  - canonical signer-facing share/copy/invitation/reminder/completion links now use `get_portal_url()` / `portal_sign_url`, not the old internal backend sign-access URL
  - base `open_sign` no longer falls back to `sign_access_url` for signer notification mail; without `open_sign_portal`, signer-facing notification URLs are treated as unavailable instead of silently emailing backend links
  - invitation/send and actionable manager resend now fail truthfully when a signer portal URL is unavailable, while reminder and signer-completion flows skip truthfully and owner-only completion/decline mail remains valid
  - atomic invitation failures now persist durable `notification_failed` audit evidence even though `action_send()` and actionable manual resend/correction still roll back their business state; this covers missing signer portal URLs, missing invitation templates, and queue exceptions without storing raw tokens or full tokenized URLs
  - fake resend chatter/link behavior was replaced with a manager-only pending-signer contact-correction/resend wizard that requires a reason, rotates the signer token every time, and either queues immediately or truthfully defers delivery until send / until the signer becomes actionable
  - notification audit events now distinguish `notification_queued`, `notification_failed`, and `notification_skipped`, and `signer_contact_corrected` records the controlled resend/correction path without storing raw tokens or full tokenized URLs
  - closeout proof now explicitly covers completion mail attachment + link semantics and backend view-arch visibility for manager-only resend vs canonical copy-link exposure
- Remaining deferred items remain deferred exactly as planned:
  - `T316`/`T317`: durable idempotency storage and replay/race semantics
  - `T37`: OTP mail / verification semantics
  - `T40`/`T41`: final completion/final PDF generation
- Current notification semantics still stop at truthful queue creation through Odoo mail; remote SMTP acceptance/open proof remains out of scope.
- If the next session starts at recurring hardening re-audit (`T610` / continuation `T118`), preserve `T17`/`T18`/`T19` invariants:
  - no direct mutation of existing audit rows outside privileged repair context
  - request-local uniqueness on audit sequence/hash
  - hash-chain continuity remains deferred to `T43` service-level logic
  - request value normalization/validation remains server-authoritative through `validation_service`
  - signer evidence fields remain format-validated server-side (`ip_last`, `consent_text_hash`, `signer_timezone`)
  - backend actions that expose operational models include `kanban` mode and remain covered by `test_sign_backend_views.py`
- Before closing each task, apply the mandatory hardening checklist and re-audit previously completed neighboring tasks when shared models/actions are touched.
- If the next session starts with cleanup, run runtime tests first and fix any failures before adding new features.
- `T35` closeout sanitization is now complete as well:
  - `notification_failed.failure_reason` stores stable safe codes only (`missing_template`, `signer_notification_url_unavailable`, `mail_queue_error`, `notification_service_error`)
  - raw notification exceptions are logged server-side and are no longer persisted in audit metadata or reflected back through atomic invitation queue error messages
  - durable failure audit for atomic invitation flows remains in place for initial send and actionable manual resend/correction
  - best-effort reminder/completion/decline and wrapper failure paths now use sanitized failure codes too
- `T36` is now closed. Additional portal security guarantees now include:
  - dedicated replay/token-abuse coverage in `addons/open_sign_portal/tests/test_portal_security.py` with shared helper extraction in `addons/open_sign_portal/tests/common.py`
  - explicit exact-match token semantics across signer page, source-PDF document route, and JSONRPC save/submit/decline endpoints for valid, wrong, near-match, missing, rotated, and mismatched-internal-user access paths
  - rotated old tokens are now proven invalid everywhere current portal auth applies, while the newly rotated token still works after manual resend/contact correction
  - stale revision, request lock contention, duplicate submit/decline replay, waiting-signer direct JSONRPC abuse, and terminal mutation denial are all explicitly covered against the current portal contract
  - waiting signers remain unable to save or submit early, can still decline, and waiting-page visits remain non-opening evidence
  - `/document` source-PDF abuse boundaries are now explicitly covered for waiting signers, terminal review states, and cancelled/voided denial paths
  - denial/error no-leak assertions now prove invalid/rotated token responses and related audit checks do not echo raw tokens or tokenized URLs
  - `T36` intentionally does not add true token expiry, rate limiting, durable idempotency/replayed-response caching, OTP flow changes, or final artifact token access; those remain deferred to `T37`, `T316`/`T317`, and `T40`/`T41`/`T47`
