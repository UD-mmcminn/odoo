# Open Sign App Feature Plan and Design Control

## Document Control

| Field | Value |
|---|---|
| Document ID | `FEATURE-OPEN-SIGN` |
| Version | `1.1.0` |
| Status | `Active (Living Document)` |
| Created | `2026-02-26` |
| Last Updated | `2026-03-12` |
| Product Area | `Open Sign Odoo Addons` |
| Primary Owner | `Engineering` |
| Review Cadence | `Weekly or at milestone close` |

## How To Use This Document

- Keep this file in source control and update it for feature-branch implementation PRs.
- Follow `AGENTS.md` start/closeout gates for each coding task.
- Use task checkboxes as the source of truth for completed and pending work.
- When scope changes, add a Change Request entry under `Design Control` before implementation.
- Do not mark a task complete unless its acceptance criteria and tests are complete.
- Run `scripts/review_gate_open_sign.sh` and complete `REVIEW_CHECKLIST.md` before closeout.
- Keep requirement, task, and milestone references consistent when adding/removing scope.

## M0 Deliverables Index

These M0 artifacts are now available and linked to `T90`-`T99`:

- [DESIGN_DATA_COLLECTION_NOTES.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/DESIGN_DATA_COLLECTION_NOTES.md) (`T90`)
- [TASK_CARDS.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/task_cards/TASK_CARDS.md) (`T91`)
- [PULL_REQUEST_TEMPLATE.md](/home/mmcminn/Projects/src/odoo/.github/PULL_REQUEST_TEMPLATE.md) Open Sign checklist block (`T92`)
- [DEVELOPER_COMMANDS.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/DEVELOPER_COMMANDS.md) (`T93`)
- [SECURITY_ACL_POLICY.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/SECURITY_ACL_POLICY.md) (`T94`)
- [PORTAL_API_CONTRACT.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/PORTAL_API_CONTRACT.md) (`T95`)
- [LEGAL_CONSENT_STRATEGY.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/LEGAL_CONSENT_STRATEGY.md) (`T96`)
- [ATTACHMENT_ACCESS_POLICY.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/ATTACHMENT_ACCESS_POLICY.md) (`T97`)
- [VALIDATION_TEST_VECTORS.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/VALIDATION_TEST_VECTORS.md) (`T98`)
- [EVIDENCE_SCHEMA_V1.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/EVIDENCE_SCHEMA_V1.md) (`T99`)

Supplemental Phase 0 artifacts:

- [WIREFRAME_APPROVAL.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/WIREFRAME_APPROVAL.md) (`T04`)
- [OBSERVABILITY_BASELINE_PROPOSAL.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/OBSERVABILITY_BASELINE_PROPOSAL.md) (`T08`)
- [MERGE_GATE_POLICY_PROPOSAL.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/MERGE_GATE_POLICY_PROPOSAL.md) (`T09`)
- [PDF_SIGNING_STACK_RECOMMENDATION.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/PDF_SIGNING_STACK_RECOMMENDATION.md) (`T05`)
- [LEGAL_ACCEPTANCE_CRITERIA.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/LEGAL_ACCEPTANCE_CRITERIA.md) (`T03`)
- [RETENTION_ARCHIVAL_PURGE_POLICY.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/RETENTION_ARCHIVAL_PURGE_POLICY.md) (`T07`)

## Review Outcomes (2026-02-26)

This revision addresses initial planning gaps found during control review:

- Added missing domain entities for signer roles and selectable field options.
- Decoupled addon dependencies so core domain logic does not depend on web/portal addons.
- Added non-functional and control requirements (security boundaries, retention, observability, migration path).
- Added explicit status transition matrix and security control checklist.
- Added unresolved design decisions and owners to avoid hidden blockers.
- Expanded task board and traceability to include control and hardening work.
- Closed traceability and milestone-gate gaps for new security/API/consent controls.
- Normalized change history and progress metrics for accurate execution tracking.
- Added a schema-level storage contract with field types, FK/ondelete policy, constraints, and model interaction notes.
- Clarified Odoo model-vs-data loading patterns and added manifest `data` load plan per addon.
- Added control coverage for endpoint idempotency/race safety, timestamp trust policy, validation taxonomy, and immutable PDF digests.
- Generated the M0 documentation package and linked all deliverables for execution tracking.
- Added immutable template versioning prior to send (`draft -> versioned -> sent`) to preserve legal document baselines.

## Concept Coverage Re-Review (2026-02-26)

| Area | Coverage Status | Evidence | Remaining Risk / Decision |
|---|---|---|---|
| Template-driven PDF signing | Covered | `R-001`, `T11`, `T21`, `T40` | PDF stack final choice (`D-001`) |
| Full field-type support (signature + form controls) | Covered | Scope + `FieldType` enum + `R-002` | Type-specific validation hardening in implementation |
| Required/optional and validation behavior | Covered | `R-003`, `T18`, `T24`, `T44` | Regex and length boundary rules must be tested per type |
| Multi-signer orchestration (sequential/parallel) | Covered | `R-004`, `T15`, `T33` | Final sequencing edge cases in declined/expired flows |
| Signature adoption + optional certificate signing | Covered | `R-005`, `R-010`, `T25`, `T50`-`T52` | Certificate path remains optional behind milestone gate |
| Status lifecycle and transition integrity | Covered | status matrix + `R-006`, `R-012`, `T06`, `T14` | Transition guard tests must include invalid state jumps |
| Immutable template version capture before send | Covered | `T06`, schema contract `open.sign.template.version` + request invariants | Enforce snapshot immutability and no post-send template drift |
| Audit evidence and consent capture | Covered | `R-007`, `R-022`, `T03`, `T43`, `T46` | Jurisdiction-specific wording still requires Legal signoff workflow |
| Portal/public signing security posture | Covered | `R-009`, `R-020`, `R-021`, `R-023`, `T31`, `T36`, `T38`, `T39` | Replay/expiry/abuse test depth to be validated in QA |
| Endpoint idempotency and race safety | Covered (this revision) | `R-024`, `T316`, `T317`, endpoint contract v1 | Retry and parallel-submit edge cases must be regression-tested |
| Timestamp trust and evidence reproducibility | Covered (this revision) | `R-025`, `R-028`, `T410`, `T411` | NTP and deployment clock-drift controls must be operationalized |
| Validation and audit taxonomy clarity | Covered (this revision) | `R-026`, `R-027`, validation matrix + audit taxonomy sections | Matrix updates must remain aligned with code and tests |
| Odoo codebase compliance and module structure | Covered | Odoo alignment principles + `R-017`, `T09`, `T69` | Must be continuously enforced in PR reviews |
| Data storage and relational design quality | Covered (this revision) | Schema contract section + `T110`, `T112` | Migration evolution discipline required across releases |

## Odoo Codebase Alignment Principles

This section captures conventions observed in this repository (`addons/*`, `odoo/addons/test_lint/*`) and is mandatory for implementation decisions:

1. Reuse Odoo primitives before introducing custom infrastructure:
- Use `portal.mixin` access tokens and `_document_check_access()` style access checks for portal links.
- Reuse existing signature UI primitives (`portal.signature_form`, `web.NameAndSignature`) where possible.

2. Keep addon structure Odoo-native:
- Require `__init__.py` at module root and every Python package used by the module.
- Keep `tests/__init__.py` with explicit `from . import test_*` imports for all test files.
- Keep JS tests under `static/tests/**/*`; include through manifest assets.

3. Follow manifest and asset conventions:
- Use only recognized manifest keys and avoid noise keys set to default values.
- Define assets in `__manifest__.py` (`assets` section), not `views/assets.xml`.
- Keep data loading order stable: security, data, views, reports, wizards.

4. Respect ORM and API lint expectations:
- Do not import `odoo.orm` directly; import from `odoo` (`api`, `fields`, `models`, `_`).
- Avoid public method argument names `ids` and `context`.
- Keep method override signatures and API decorators compatible with parent methods.
- Use `models.Constraint(...)` and explicit field indexes where needed.

5. Follow controller/route patterns:
- Use `type='jsonrpc'` for RPC-style endpoints; reserve `type='http'` for page rendering/download.
- Mark read-only routes with `readonly=True` when they do not write.
- Avoid redundant route parameter redeclarations in inherited routes.

6. Align security, multi-company, and i18n behavior:
- Enforce multi-company record rules on all business models containing `company_id`.
- Use `consteq`-safe token comparisons and test replay/expiry paths.
- Use `_t` for JS translations and `.translate` for user-visible OWL component props.

## Junior Developer Delivery Pack

This section is intentionally explicit to support lower-experience implementers.

### Mandatory Implementation Sequence

1. Build core models and security first (`open_sign`) before any UI/controller work.
2. Add server-side validation before client-side validation.
3. Add portal access checks before exposing public routes.
4. Add tests for each behavior in the same PR that adds the behavior.
5. Add migration hooks and indexes before declaring backend complete.
6. Add observability and hardening before UAT/release signoff.
7. For Phase 2 (`open_sign_web`), keep client validation UX-only and never bypass/replace server-authoritative model constraints.

### Definition of Ready (DoR) For Any Task

- Requirement ID(s) linked.
- Dependencies identified and complete.
- Target files identified.
- Impacted schema-contract model rows identified (for any persisted data change).
- Security implications documented.
- Test approach identified (unit/integration/http/tour/js).
- Acceptance criteria written in verifiable form.

### Task Card Template (Use For Every New Task)

```text
Task ID:
Goal:
Requirements:
Dependencies:
Target Files:
Implementation Notes:
Acceptance Criteria:
Test Plan:
Security Notes:
Rollback/Migration Impact:
```

### Pull Request Checklist (Junior-Friendly)

- Scope is limited to one coherent slice.
- Data model changes include constraints + indexes + FK `ondelete` policy + access rules.
- Server-authoritative fields are explicitly protected from direct client/user writes.
- Controllers include auth mode, access checks, and readonly declaration rationale.
- Public endpoints include abuse and replay test coverage.
- New tests are imported in `tests/__init__.py`.
- Manifest `data` ordering and asset declarations are validated.
- `scripts/review_gate_open_sign.sh` has been run (or any deferral is tracked with task ID and risk).
- `REVIEW_CHECKLIST.md` is completed and reviewed before task closure.
- For feature branches: `FEATURE.md` updated (task status, traceability, and update log).

## Odoo Design Data Collection Map

Use this as mandatory design research before implementation of each subsystem.

| Area | Reference File | What To Extract |
|---|---|---|
| Portal token model | `addons/portal/models/portal_mixin.py` | `access_token` lifecycle, URL generation, token semantics |
| Portal access guard | `addons/portal/controllers/portal.py` | `_document_check_access` and `consteq` usage |
| Signature portal flow | `addons/sale/controllers/portal.py` | `jsonrpc` accept flow, public token auth, signature write flow |
| Reusable signature UI | `addons/portal/views/portal_templates.xml` + `addons/portal/static/src/signature_form/signature_form.js` | Existing portal signature component contract and props |
| Manifest conventions | `odoo/addons/test_lint/tests/test_manifests.py` + `addons/sale/__manifest__.py` | valid keys, defaults, and asset declaration style |
| Module/test structure | `odoo/addons/test_lint/tests/test_dunderinit.py` + `odoo/addons/test_lint/tests/test_test_holes.py` + `addons/sale/tests/__init__.py` | required `__init__.py` and test import expectations |
| ACL and record rule patterns | `addons/sale/security/ir.model.access.csv`, `addons/sale/security/ir_rules.xml`, `addons/hr/security/hr_security.xml` | multi-company and group-scoped rule style |
| Model field conventions | `addons/sale/models/sale_order.py`, `addons/account/models/account_move.py` | `_check_company_auto`, `tracking`, `check_company`, constraints, index patterns |
| Test style conventions | `addons/sale/tests/test_controllers.py`, `addons/sale/tests/test_access_rights.py` | `HttpCase`/`TransactionCase`, tagging, portal access test style |
| Binary/tokenized attachment access | `addons/web/controllers/binary.py`, `addons/web/tests/test_image.py`, `addons/mail/models/ir_attachment.py` | limited token scope, expiry behavior, and attachment token usage |
| Chatter/audit integration patterns | `addons/mail/models/mail_thread.py`, `addons/mail/models/mail_message.py` | message posting patterns and thread-side effects |
| API/lint constraints | `odoo/addons/test_lint/tests/test_naming.py`, `test_orm_import.py`, `test_override_signatures.py`, `test_onchange_domains.py` | public API naming, imports, override signatures, onchange limits |
| Index and SQL expectations | `odoo/addons/test_lint/tests/test_index.py` | inverse-field index expectations (`btree`/`btree_not_null`) |
| i18n rules (JS/XML) | `odoo/addons/test_lint/tests/test_jstranslate.py`, `test_i18n.py` | `_t` usage and translatable prop conventions |
| Migration conventions | existing `addons/*/migrations/*` and `addons/*/upgrades/*` scripts | script placement and upgrade strategy style |
| Retry/idempotency behavior patterns | `addons/payment/models/payment_transaction.py`, `addons/portal/tests/test_addresses.py` | duplicate-request handling and safe retry expectations |
| UTC datetime normalization patterns | `addons/mail/models/mail_mail.py`, `addons/mail/models/mail_template.py` | canonical UTC storage and parsing expectations |
| PDF cryptographic signing internals | `odoo/tools/pdf/signature.py` | feasibility and constraints for optional certificate addon |

### Design Data Collection Log

| Item | Owner | Status | Notes |
|---|---|---|---|
| Portal/token reference notes | Backend | `Completed` | See [DESIGN_DATA_COLLECTION_NOTES.md](/home/mmcminn/Projects/src/odoo/doc/open_sign/m0/DESIGN_DATA_COLLECTION_NOTES.md). |
| Signature UI reuse decision memo | Web | `Completed` | Reuse decision recorded in design notes and ADRs. |
| Lint constraints summary | Backend | `Completed` | Lint constraints recorded with reference links. |
| ACL and record rule pattern notes | Backend/Security | `Completed` | Security matrix and policy finalized in M0 docs. |
| Model field convention notes | Backend | `Completed` | Schema contract finalized in `FEATURE.md`. |
| Test style convention notes | QA/Backend | `Completed` | Test strategy references captured in design notes. |
| Binary and attachment token notes | Backend/Security | `Completed` | Tokenized artifact policy finalized. |
| Mail thread/chatter integration notes | Backend | `Completed` | Chatter/audit integration notes captured. |
| Migration pattern summary | Backend | `Completed` | Migration strategy and hooks captured (`T112` linkage). |
| Retry/idempotency pattern summary | Backend | `Completed` | Idempotency model/policy finalized in M0 docs. |
| UTC timestamp handling summary | Backend/Ops | `Completed` | UTC trust policy and evidence rules finalized. |
| Certificate feasibility summary | Backend/Security | `Completed` | Feasibility constraints documented for optional addon. |

## Scope Summary

Build an Odoo Community replacement for the Enterprise Signature app with:

- Template-based document signing.
- Configurable, editable fields (required/optional): `signature`, `initials`, `name`, `email`, `phone`, `company`, `text`, `multiline`, `checkbox`, `radio`, `selection`, `date`, `strikethrough`, `stamp`.
- Multi-signer workflows (sequential and parallel).
- Signature adoption methods (draw, type, upload).
- Signature blocks are optional per workflow; non-signature acknowledgement flows are supported.
- Document lifecycle and status tracking.
- Full audit trail.
- Optional certificate-based digital signing module.

Out of scope for MVP:

- Third-party trust service integrations requiring paid external services.
- Jurisdiction-specific legal certification beyond audit/evidence controls.
- In-person identity validation/KYC integrations.

## Design Control

### Requirements Baseline

| Req ID | Requirement | Priority | Status |
|---|---|---|---|
| `R-001` | Upload/use PDF templates and place fields by page coordinates | Must | `Open` |
| `R-002` | Support all required field types listed in scope | Must | `Open` |
| `R-003` | Required/optional behavior per field with validation | Must | `Open` |
| `R-004` | Multi-signer workflows with role assignment | Must | `Open` |
| `R-005` | Signature adoption: draw/type/upload | Must | `Open` |
| `R-006` | Document statuses and transition logging | Must | `Open` |
| `R-007` | Audit trail capturing who/when/how signed | Must | `Open` |
| `R-008` | Final signed PDF generation and storage | Must | `Open` |
| `R-009` | Portal/public signing links with secure tokens | Must | `Open` |
| `R-010` | Optional certificate digital signing at completion | Should | `Open` |
| `R-011` | Multi-company ACL isolation and least-privilege access model | Must | `Open` |
| `R-012` | Enforced status transition rules and invalid-transition rejection | Must | `Open` |
| `R-013` | Evidence retention and export policy support | Must | `Open` |
| `R-014` | Backward-compatible schema migration strategy across module versions | Must | `Open` |
| `R-015` | Operational observability (metrics, key events, failure diagnosis) | Should | `Open` |
| `R-016` | Optional signer identity verification step (email OTP at minimum) | Should | `Open` |
| `R-017` | Conformance with Odoo lint and addon structure conventions in this repository | Must | `Open` |
| `R-018` | Task execution must follow documented DoR/Task Card/PR checklist process | Must | `Open` |
| `R-019` | Design decisions must cite concrete Odoo code references before implementation | Must | `Open` |
| `R-020` | Security groups and ACL/record-rule matrix explicitly defined and tested | Must | `Open` |
| `R-021` | Portal `jsonrpc` endpoint contract (payloads, responses, error codes) documented and tested | Must | `Open` |
| `R-022` | Signer consent/legal disclosure snapshot captured as part of audit evidence | Must | `Open` |
| `R-023` | Signed artifacts and payload attachments follow tokenized binary access policy | Must | `Open` |
| `R-024` | Mutating signer endpoints (`save`, `submit`, `decline`) are idempotent and race-safe | Must | `Open` |
| `R-025` | Evidence timestamps are canonical UTC from trusted server clock policy (drift-controlled) | Must | `Open` |
| `R-026` | Field-type validation and normalization matrix is documented and enforced client/server | Must | `Open` |
| `R-027` | Audit event taxonomy and evidence package schema are versioned and backward-compatible | Must | `Open` |
| `R-028` | Source and final PDF SHA-256 digests are stored immutably for integrity verification | Must | `Open` |
| `R-029` | Requests require at least one participant role/signer, while signature fields remain optional for non-signature acknowledgement workflows | Must | `Open` |

### Design Control Block

| Control Item | Definition |
|---|---|
| Architecture Owner | Backend Lead |
| UX Owner | Frontend/Odoo Web Lead |
| Security Owner | Platform/Security Lead |
| Data Classification | Sensitive business documents + PII |
| Compliance Considerations | IP logging, timestamping, consent evidence, retention policy |
| Risk Level | High (document integrity, signer identity, legal workflows) |
| Release Gates | Design Freeze -> MVP QA Pass -> UAT Signoff -> Production |

### Security Control Checklist

| Control ID | Control | Status |
|---|---|---|
| `SC-001` | Portal links use `portal.mixin` token lifecycle and constant-time token checks | `Open` |
| `SC-002` | Token expiry and replay prevention | `Open` |
| `SC-003` | Multi-company record rules validated with tests | `Open` |
| `SC-004` | Audit log immutability constraints enforced post-completion | `Open` |
| `SC-005` | PII minimization and retention enforcement | `Open` |
| `SC-006` | Rate limit or abuse controls on public signing endpoints | `Open` |
| `SC-007` | Idempotency keys and duplicate-submit protection on mutating portal endpoints | `Open` |
| `SC-008` | Concurrency control prevents double-transition races in signer completion/decline | `Open` |
| `SC-009` | Trusted timestamp source policy (UTC clock, drift alerts) for legal evidence | `Open` |

### Security Roles and ACL Matrix (Baseline)

| Group | Purpose | Key Model Access |
|---|---|---|
| `open_sign.group_open_sign_user` | Operational users creating templates/requests | R/W/C on templates, requests, request values in allowed companies |
| `open_sign.group_open_sign_manager` | Administration and exception handling | Full access to operational models; void/cancel authority |
| `open_sign.group_open_sign_auditor` | Read-only compliance/audit review | Read-only on requests, signers, values, audit logs |
| `base.group_portal` (token-scoped) | External signer access | No direct model ACL write; route-mediated token-scoped actions only |

Implementation notes:

- External signers must access data only through token-validated controller flows.
- Audit models should be non-editable for non-manager roles after completion/void.
- Multi-company rules must be explicit on every business model with `company_id`.

### Assumptions and Open Decisions

| ID | Decision Needed | Owner | Due | Status |
|---|---|---|---|---|
| `D-001` | Select PDF rendering/writing library stack for field flattening | Backend | `M0` | `Resolved (core deterministic flattening path approved in T05)` |
| `D-002` | Select certificate implementation approach (`pyHanko` vs OpenSSL wrapper) | Backend/Security | `M0` | `Resolved (pyHanko preferred for optional certificate addon)` |
| `D-003` | Confirm legal baseline for consent language and evidence content | Product/Legal | `M0` | `Resolved (US ESIGN + UETA baseline; Legal wording signoff required)` |
| `D-004` | Confirm OTP requirement for MVP vs post-MVP | Product/Security | `M0` | `Deferred (post-MVP default; revisit before T37)` |
| `D-005` | Define retention period and purge schedule by document class | Product/Ops | `M1` | `Resolved (Configurable retention/purge with legal-hold override)` |
| `D-006` | Finalize signer portal UX reuse level (`portal.signature_form` vs dedicated component) | Web Lead | `M0` | `Resolved (wireframe pack v1 approved)` |
| `D-007` | Define production clock drift tolerance and monitoring policy for legal timestamps | Platform/Ops | `M0` | `Resolved (Policy v1)` |
| `D-008` | Approve field-level validation matrix defaults (length/date/format constraints) | Product/Backend | `M0` | `Resolved (Matrix v1)` |
| `D-009` | Approve evidence package schema v1 and event taxonomy versioning policy | Product/Backend | `M0` | `Resolved (Schema v1)` |
| `D-010` | Confirm whether a signature block is mandatory for completion workflows | Product/Backend | `M1` | `Resolved (participant required; signature field optional)` |
| `D-011` | Approve external email-signer magic-link policy (TTL, one-time vs multi-use, resend/rotation, revoke semantics) | Product/Security | `M2` | `Open` |

### Phase 0 Decisions Locked (2026-02-26)

- `T01`: Target platform is Odoo `19.0` (repository baseline), with runtime compatibility aligned to repository constraints (`Python 3.10-3.13`, PostgreSQL `>= 13`).
- `T02`: Addon structure/install order approved: `open_sign` -> `open_sign_web` -> `open_sign_portal` -> optional `open_sign_certificate`.
- `T03`: Legal baseline set to US `ESIGN` + `UETA`, with ESIGN federal coverage treated as highest priority.
- `T04`: Wireframe approval pack accepted for editor + portal + immutable versioning UX.
- `T05`: PDF strategy approved: deterministic flattened final PDF in core; optional digital certificate signing via `pyHanko`.
- `T06`: Status flow approved with immutable versioning stage: `draft -> versioned -> sent` before signer actions.
- `T07`: Retention/purge policy approved as configurable; default retention is indefinite; purge can only occur after retention window; legal hold always overrides purge.
- `T08`: Observability baseline approved (events, metrics, alerts, and dashboard set).
- `T09`: Merge gates approved with policy change: full `FEATURE.md` updates are required for feature branches.

### Change Control Log

| CR ID | Date | Change | Impact | Decision |
|---|---|---|---|---|
| `CR-000` | `2026-02-26` | Initial baseline for Open Sign app | New feature | Approved |
| `CR-001` | `2026-02-26` | Added missing control requirements, entity fixes, dependency corrections | Plan quality and execution risk | Approved |
| `CR-002` | `2026-02-26` | Added Odoo codebase alignment controls and module structure adjustments | Conformance and maintainability | Approved |
| `CR-003` | `2026-02-26` | Added junior-focused delivery controls and Odoo design data collection map | Execution quality and onboarding risk | Approved |
| `CR-004` | `2026-02-26` | Final comprehensive quality review updates (traceability, milestones, risks, metrics) | Completeness and governance accuracy | Approved |
| `CR-005` | `2026-02-26` | Added detailed schema storage contract (field types, FK/ondelete, constraints, interactions) | Data model quality and implementation consistency | Approved |
| `CR-006` | `2026-02-26` | Added explicit Odoo data-loading model, manifest load plan, and missing portal security artifacts | Implementation clarity and Odoo-conformance risk reduction | Approved |
| `CR-007` | `2026-02-26` | Added idempotency/timestamp/validation-taxonomy/integrity-digest controls and tasks | Legal-evidence robustness and implementation ambiguity reduction | Approved |
| `CR-008` | `2026-02-26` | Generated M0 documentation deliverables bundle (`T90`-`T99`) and linked artifacts | Execution readiness and junior handoff quality | Approved |
| `CR-009` | `2026-02-26` | Applied Phase 0 decision updates (`T01/T02/T03/T06/T07`) including immutable template versioning and planning artifacts for `T04/T05/T08/T09` | Design completeness and implementation guardrail quality | Approved |
| `CR-010` | `2026-02-26` | Applied final Phase 0 approvals (`T04/T05/T08/T09`) and feature-branch-only `FEATURE.md` merge-gate rule | M0 closure and workflow policy refinement | Approved |
| `CR-011` | `2026-02-27` | Clarified workflow invariant: at least one participant role/signer is required for send flows, but signature fields are optional | Prevents false signature-field dependency and preserves form/acknowledgement use cases | Approved |
| `CR-012` | `2026-02-28` | Added deferred external email-signer authentication track (magic-link token lifecycle, expiry/revocation, and abuse-test coverage) | Clarifies scope and sequencing for unauthenticated signer support without weakening ACL posture | Approved |

### Architecture Decisions (ADRs Summary)

| ADR ID | Decision | Status |
|---|---|---|
| `ADR-001` | Split implementation into core + web + portal + certificate addons | Accepted |
| `ADR-002` | Store field positions normalized by page dimensions | Accepted |
| `ADR-003` | Use immutable audit log records after completion | Accepted |
| `ADR-004` | Certificate signing implemented as optional extension addon | Accepted |
| `ADR-005` | Keep core addon independent of website/portal/web-specific UI concerns | Accepted |
| `ADR-006` | Implement portal signer access via `portal.mixin` extension on signer model | Accepted |
| `ADR-007` | Use manifest-declared assets and `static/tests` for JS tests | Accepted |
| `ADR-008` | Require idempotency keys and row-level locking for mutating portal signer endpoints | Accepted |
| `ADR-009` | Version audit event taxonomy and evidence package schema from v1 onward | Accepted |
| `ADR-010` | Require immutable template version snapshots before sending requests (`draft -> versioned -> sent`) | Accepted |
| `ADR-011` | Enforce participant-required send flows while keeping signature fields optional | Accepted |

## Addons To Create

| Addon | Purpose | Depends On | DB Entities |
|---|---|---|---|
| `open_sign` | Core business domain, workflows, statuses, PDF finalization, audit backbone | `base`, `mail` | Yes |
| `open_sign_web` | Internal template editor and backend web client components/widgets | `open_sign`, `web` | Optional minimal |
| `open_sign_portal` | Public/portal signing routes, token validation, signer UX, reminders | `open_sign`, `portal`, `website` | Yes |
| `open_sign_certificate` | Optional PKI digital signature and certificate verification metadata | `open_sign` | Yes |

Install order (approved):

1. `open_sign`
2. `open_sign_web`
3. `open_sign_portal`
4. `open_sign_certificate` (optional)

---

## Odoo Data Pattern: Models vs XML/CSV Records

This is the core distinction used across official addons and must be followed in this feature:

- `models/*.py` defines schema and behavior (`fields.*`, constraints, business logic). This is where database table/column design lives.
- XML/CSV files loaded via `__manifest__.py['data']` create/update records in existing models (for example `ir.ui.view`, `ir.actions.*`, `mail.template`, `ir.sequence`, `res.groups`, `ir.rule`, and business seed records).
- `views/*.xml` are also data records (`ir.ui.view`) even though they are kept in a `views/` directory.
- `data/*.xml` typically stores seed/config records and automation metadata (cron, mail templates, subtype, defaults, sequences).
- `security/*.csv` and `security/*.xml` store ACL and record-rule records; they do not define Python model fields.
- Not every addon requires a `data/` folder; addons that only extend behavior can have model code with minimal or no XML data loading.

### Manifest Data Loading Plan (v1)

Planned `__manifest__.py['data']` loading order by addon:

1. `open_sign`
- `security/open_sign_groups.xml`
- `security/ir.model.access.csv`
- `security/open_sign_security.xml`
- `data/sequence.xml`
- `data/mail_templates.xml`
- `data/ir_cron.xml`
- `views/sign_template_views.xml`
- `views/sign_role_views.xml`
- `views/sign_request_views.xml`
- `views/sign_audit_views.xml`
- `views/sign_menus.xml`
- `report/sign_completion_certificate.xml`

2. `open_sign_web`
- No required server-side XML records for MVP.
- Frontend assets are declared in manifest `assets` and loaded from `static/src/**/*`.
- If server-registered actions/views are later introduced, add `views/*.xml` entries explicitly.

3. `open_sign_portal`
- `security/ir.model.access.csv`
- `security/open_sign_portal_security.xml`
- `data/mail_templates.xml`
- `views/portal_templates.xml`

4. `open_sign_certificate` (optional)
- `security/ir.model.access.csv`
- `views/certificate_profile_views.xml`
- Add `data/*.xml` only if certificate defaults/system parameters are introduced.

### XML Record Mutability and External ID Policy

Use this baseline to avoid upgrade surprises:

| Record Category | `noupdate` Default | External ID Convention | Notes |
|---|---|---|---|
| Security (`res.groups`, `ir.model.access`, `ir.rule`) | `1` | `open_sign.<purpose>_<name>` | Security records should not be silently overwritten on module update. |
| System behavior (`ir.cron`, `ir.sequence`, config parameters) | `1` | `open_sign.<model_short>_<name>` | Preserve operator adjustments unless intentionally managed by migration scripts. |
| Notification templates (`mail.template`, `mail.message.subtype`) | `1` | `open_sign.mail_<name>` | Preserve business customizations post-deployment. |
| Views and actions (`ir.ui.view`, `ir.actions.*`, menus) | `0` | `open_sign.view_<name>`, `open_sign.action_<name>`, `open_sign.menu_<name>` | Must evolve with code and be updated on module upgrade. |
| Demo data | `1` | `open_sign.demo_<name>` | Isolated under `demo` manifest key; never required for production behavior. |

## Addon Specification: `open_sign`

### Interfaces

- Python model APIs:
  - `open.sign.template.action_publish()`
  - `open.sign.template.action_publish_version()`
  - `open.sign.template.action_archive()`
  - `open.sign.request.action_version()`
  - `open.sign.request.action_send()`
  - `open.sign.request.action_cancel()`
  - `open.sign.request.action_complete()`
  - `open.sign.request.action_void(reason=None)`
  - `open.sign.request._compute_status()`
  - `open.sign.request._check_transition(target_status)`
  - `open.sign.request.generate_final_pdf()`
- Service helpers:
  - `pdf_field_mapper.apply_values_to_pdf()`
  - `audit_service.log_event()`
  - `validation_service.validate_field_value()`
- XML/UI interfaces:
  - Menu/actions for templates, requests, and audit logs.
  - Form/tree/kanban views for operational users.

### Database Entities

1. `open.sign.template`
- Core fields: `name`, `state`, `source_attachment_id`, `active`, `company_id`, `owner_id`.
- Relations: `field_ids`, `request_ids`, `role_ids`, `version_ids`.

2. `open.sign.template.version`
- Core fields: `template_id`, `version_number`, `source_attachment_id`, `source_pdf_sha256`, `field_snapshot_json`, `role_snapshot_json`, `published_at`, `published_by`, `state`.
- Purpose: immutable sendable snapshot of template structure and source artifact.

3. `open.sign.role`
- Core fields: `name`, `template_id`, `sequence`, `required`, `color`.
- Purpose: signer slot abstraction to map fields and request signers reliably.

4. `open.sign.template.field`
- Core fields: `template_id`, `type`, `label`, `required`, `page`, `x`, `y`, `width`, `height`, `role_id`, `sequence`, `default_value`, `validation_regex`, `max_length`, `min_length`.
- Constraints: coordinates in normalized range; width/height > 0.

5. `open.sign.template.field.option`
- Core fields: `field_id`, `value`, `label`, `sequence`, `is_default`.
- Scope: radio and selection field option definitions.

6. `open.sign.request`
- Core fields: `name`, `template_id`, `template_version_id`, `status`, `sent_at`, `completed_at`, `expires_at`, `final_attachment_id`, `source_pdf_sha256`, `final_pdf_sha256`, `owner_id`, `company_id`, `ordered_signing`, `evidence_schema_version`, `lock_version`.
- Computed/counters: `signed_count`, `pending_count`, `declined_count`, `last_event_at`.

7. `open.sign.request.signer`
- Core fields: `request_id`, `partner_id`, `email`, `role_id`, `sequence`, `state`, `signed_at`, `declined_reason`, `last_opened_at`, `ip_last`, `consent_accepted_at`, `consent_text_hash`, `signer_timezone`.
- Constraints: unique per `(request_id, role_id)`.

8. `open.sign.request.value`
- Core fields: `request_id`, `template_field_id`, `signer_id`, `value_text`, `value_json`, `signed_payload_attachment_id`, `is_valid`.
- Constraints: unique per `(request_id, template_field_id, signer_id)`.

9. `open.sign.audit.log`
- Core fields: `request_id`, `signer_id`, `event_type`, `event_sequence`, `event_at`, `ip`, `user_agent`, `metadata_json`, `hash_chain`, `previous_hash`, `consent_text_hash`.
- Constraints: append-only after completion/void.

### Status Transition Matrix

| From | Allowed To |
|---|---|
| `draft` | `versioned`, `cancelled` |
| `versioned` | `sent`, `cancelled` |
| `sent` | `opened`, `in_progress`, `declined`, `expired`, `cancelled` |
| `opened` | `in_progress`, `declined`, `expired`, `cancelled` |
| `in_progress` | `partially_signed`, `completed`, `declined`, `expired`, `cancelled` |
| `partially_signed` | `in_progress`, `completed`, `declined`, `expired`, `cancelled` |
| `completed` | `voided` |
| `declined` | `cancelled` |
| `expired` | `cancelled` |
| `cancelled` | (terminal) |
| `voided` | (terminal) |

### Planned Folder Tree

```text
addons/open_sign/
  __init__.py                        # Module init
  __manifest__.py                    # Dependencies, data files
  security/
    open_sign_groups.xml            # open_sign user/manager/auditor groups
    ir.model.access.csv              # ACLs for internal users
    open_sign_security.xml           # Record rules (owner/company scope)
  models/
    __init__.py
    sign_template.py                 # open.sign.template model + lifecycle methods
    sign_template_version.py         # immutable template snapshot model used before sending
    sign_role.py                     # open.sign.role model
    sign_template_field.py           # open.sign.template.field model + validation
    sign_template_field_option.py    # option model for radio/selection fields
    sign_request.py                  # open.sign.request model + state engine
    sign_request_signer.py           # signer model + sequencing and transitions
    sign_request_value.py            # per-field captured values and normalization
    sign_audit_log.py                # immutable audit log model
  services/
    __init__.py
    pdf_field_mapper.py              # apply_values_to_pdf(), flatten_fields()
    audit_service.py                 # log_event(), compute_hash_chain()
    validation_service.py            # validate_field_value(type, required, rules)
    transition_service.py            # _check_transition and transition helpers
  wizards/
    __init__.py
    sign_send_wizard.py              # request send/reminder workflow helper
  data/
    mail_templates.xml               # send/reminder/completion notifications
    ir_cron.xml                      # reminders + expiration jobs
    sequence.xml                     # document/request sequence definitions
  views/
    sign_template_views.xml          # template menu/tree/form
    sign_role_views.xml              # signer role views
    sign_request_views.xml           # request menu/tree/form/kanban
    sign_audit_views.xml             # audit log visibility for admins
    sign_menus.xml                   # top-level menu/actions
  report/
    sign_completion_certificate.xml  # evidence summary page template
  tests/
    __init__.py
    test_sign_request_flow.py        # core lifecycle and status transitions
    test_field_validation.py         # required/optional + type validation tests
    test_access_rules.py             # multi-company and ACL checks
    test_audit_integrity.py          # immutable audit/hash assertions
```

### Datatypes and Enums

- `FieldType`: `signature`, `initials`, `name`, `email`, `phone`, `company`, `text`, `multiline`, `checkbox`, `radio`, `selection`, `date`, `strikethrough`, `stamp`.
- `RequestStatus`: `draft`, `versioned`, `sent`, `opened`, `in_progress`, `partially_signed`, `completed`, `declined`, `expired`, `cancelled`, `voided`.
- `SignerState`: `pending`, `opened`, `signed`, `declined`, `expired`.
- `SignatureMethod`: `draw`, `type`, `upload`, `certificate`.
- `AuditEventType`: `request_created`, `template_version_published`, `request_versioned`, `request_sent`, `signer_opened`, `value_saved`, `signer_submitted`, `signer_declined`, `request_completed`, `request_expired`, `request_voided`, `otp_requested`, `otp_verified`, `artifact_generated`, `artifact_downloaded`.
- JSON payload types:
  - `value_json` for structured values (checkbox, radio, selection, date metadata).
  - `metadata_json` for audit details.

### Field Validation and Normalization Matrix (v1)

| Field Type | Expected Input | Normalized Storage | Required Validation Rules |
|---|---|---|---|
| `signature` | draw strokes, typed render, or uploaded image payload | `value_json` (`method`, `display_name`, optional stroke metadata) + `signed_payload_attachment_id` when binary payload exists | payload present; allowed mime types; size cap; signer matches role |
| `initials` | short text or rendered initials payload | `value_text` uppercase (and payload attachment if rendered image) | min 1 char, max 8 chars |
| `name` | free text | `value_text` trimmed | min/max length; no control chars |
| `email` | email address | `value_text` lowercase trimmed | strict email regex; length <= 254 |
| `phone` | phone number string | `value_text` E.164-normalized where possible | digits/`+` validation; length bounds |
| `company` | free text | `value_text` trimmed | min/max length; no control chars |
| `text` | single-line text | `value_text` trimmed | no newlines; min/max length |
| `multiline` | multi-line text | `value_text` normalized line endings (`\n`) | min/max length; newline allowed |
| `checkbox` | boolean | `value_json` boolean | value must be `true`/`false` |
| `radio` | single option key | `value_text` option key | must match active option set for field |
| `selection` | single option key | `value_text` option key | must match active option set for field |
| `date` | date value | `value_json` (`iso_date`, optional `timezone`) | ISO-8601 date; optional range checks |
| `strikethrough` | marker acknowledgement | `value_json` (`applied`: true/false) | boolean only; no free text payload |
| `stamp` | uploaded stamp image/payload | `value_json` (`stamp_type`, optional label) + `signed_payload_attachment_id` | payload required; allowed mime types; size cap |

Normalization rules:

- Server normalization is authoritative; client normalization is best-effort UX.
- Invalid values must fail with `validation_error` and field-level detail payload.
- `radio` and `selection` values are persisted as canonical option keys, never labels.

### Audit Event Taxonomy and Evidence Schema (v1)

Audit event taxonomy baseline:

| Event Type | Actor Context | Required Metadata Keys | Transition Impact |
|---|---|---|---|
| `request_created` | internal user | `request_id`, `template_id` | sets `draft` |
| `template_version_published` | internal user | `template_id`, `template_version_id`, `version_number` | none |
| `request_versioned` | internal user/system | `request_id`, `template_version_id`, `source_pdf_sha256` | `draft` -> `versioned` |
| `request_sent` | internal user/system | `request_id`, `recipient_count` | `versioned` -> `sent` |
| `signer_opened` | signer | `request_id`, `signer_id`, `ip`, `user_agent` | `sent`/`pending` visibility updates |
| `value_saved` | signer | `request_id`, `signer_id`, `field_count` | none |
| `signer_submitted` | signer | `request_id`, `signer_id`, `signature_method`, `idempotency_key` | signer state -> `signed` |
| `signer_declined` | signer | `request_id`, `signer_id`, `reason` | request may move to `declined` |
| `otp_requested` | signer/system | `request_id`, `signer_id` | none |
| `otp_verified` | signer/system | `request_id`, `signer_id` | unlocks submit when OTP enabled |
| `artifact_generated` | system | `request_id`, `final_attachment_id`, `final_pdf_sha256` | supports `completed` |
| `request_completed` | system | `request_id`, `completed_at` | -> `completed` |
| `request_expired` | system/cron | `request_id`, `expires_at` | -> `expired` |
| `request_voided` | manager | `request_id`, `reason` | `completed` -> `voided` |
| `artifact_downloaded` | user/signer | `request_id`, `attachment_id`, `access_mode` | none |

Evidence package schema v1 minimum sections:

- `meta`: `schema_version`, export timestamp UTC, exporter identity.
- `request`: core request fields, status timeline, digest fields.
- `signers`: signer states, timestamps, consent evidence.
- `values`: normalized field captures.
- `audit`: ordered audit events with hash-chain metadata.
- `artifacts`: source/final attachment references and SHA-256 digests.

---

## Addon Specification: `open_sign_web`

### Phase 2 Guardrails (Derived From M1 Outcomes)

- Client/editor validation is convenience only; server validation and normalization (`open_sign` models/services) remain authoritative.
- Editor payload serialization must align with backend schema constraints (geometry bounds, required labels, non-negative sequence, option/value normalization).
- Frontend components must not write server-authoritative lifecycle/control fields (`state`, `signed_at`, audit chain data, validation authority flags).
- Every `open_sign_web` PR must run both web scope tests and full backend regression (`/open_sign`) before merge.
- Deferred M1 items remain out of M2 scope unless explicitly scheduled: `DQ-001` (`T35` notifications) and `DQ-002` (`T43` hash-chain continuity service checks).

### Interfaces

- OWL components/services:
  - `TemplateCanvas` (drag/drop field placement)
  - `FieldPalette` (field type toolbox)
  - `SignerPreviewPanel` (role-specific view)
  - `SignatureAdoptionDialog` (draw/type/upload)
  - `FieldPropertiesPanel` (required, validation, defaults)
- JS service contracts:
  - `serializeFieldGeometry()`
  - `validateClientFieldValue()`
  - `normalizeCanvasToPdfCoordinates()`

### Database Entities

- Optional: `open.sign.ui.preset` for reusable style presets.

### Planned Folder Tree

```text
addons/open_sign_web/
  __init__.py
  __manifest__.py
  static/src/
    js/
      template_canvas.js             # place/move/resize field overlays
      field_palette.js               # field add/edit interactions
      field_properties_panel.js      # field settings editor
      signer_preview_panel.js        # role-specific preview in editor
      signature_adoption_dialog.js   # draw/type/upload signature collection
      signing_form.js                # client validation + submission payload
    xml/
      template_canvas.xml            # OWL templates for editor UI
      field_properties_panel.xml     # editor side panel template
      signature_adoption_dialog.xml  # dialog template
      signing_form.xml               # signer UI template
    scss/
      open_sign.scss               # editor and signer styling
  static/tests/
    test_template_canvas.test.js          # coordinate and drag/drop behavior
    test_signing_form.test.js             # client validation and field rendering
    test_coordinate_normalization.test.js # canvas/pdf mapping checks
```

### Datatypes

- `FieldGeometry`: `page: int`, `x: float`, `y: float`, `width: float`, `height: float`.
- `FieldValuePayload`: `field_id: int`, `type: string`, `value: string|bool|object`.

---

## Addon Specification: `open_sign_portal`

### Interfaces

- HTTP routes/controllers:
  - `GET /my/sign/<int:signer_id>?access_token=...`: open signing page.
  - `POST /my/sign/<int:signer_id>/save` (`jsonrpc`): save draft values.
  - `POST /my/sign/<int:signer_id>/submit` (`jsonrpc`): submit signer completion.
  - `POST /my/sign/<int:signer_id>/decline` (`jsonrpc`): decline with reason.
  - `POST /my/sign/<int:signer_id>/otp/request` (`jsonrpc`, optional): issue OTP challenge.
  - `POST /my/sign/<int:signer_id>/otp/verify` (`jsonrpc`, optional): verify signer OTP.
- Mail integrations:
  - Invitation, reminder, completion, decline notifications.

### Portal Endpoint Contract (v1)

- `POST /my/sign/<int:signer_id>/save` (`jsonrpc`)
  - Request: `{"values": [{"field_id": int, "value": any}], "client_ts": iso_datetime, "idempotency_key": "uuid", "request_revision": int}`
  - Response success: `{"ok": true, "state": "in_progress", "request_revision": int}`
  - Response error: `{"ok": false, "error_code": "...", "message": "..."}`
- `POST /my/sign/<int:signer_id>/submit` (`jsonrpc`)
  - Request: `{"values": [...], "signature_method": "draw|type|upload", "consent": {"accepted": true, "text_hash": "..."}, "idempotency_key": "uuid", "request_revision": int}`
  - Response success: `{"ok": true, "force_refresh": true, "redirect_url": "..."}`
  - Response error: `{"ok": false, "error_code": "...", "message": "..."}`
- `POST /my/sign/<int:signer_id>/decline` (`jsonrpc`)
  - Request: `{"reason": "...", "idempotency_key": "uuid", "request_revision": int}` (reason non-empty)
  - Response: same `ok/error_code/message` envelope

Standard `error_code` values:

- `invalid_token`
- `expired_token`
- `signing_order_blocked`
- `validation_error`
- `consent_required`
- `request_locked`
- `idempotency_conflict`
- `stale_revision`

### Database Entities

1. `open.sign.request.signer` (extension via `_inherit`)
- Inherits `portal.mixin` in this addon to leverage standard `access_token`, `access_url`, and share URL behavior.
- Adds portal helpers for URL generation and access checks.

2. `open.sign.signing.session` (optional hardening)
- Fields: `request_signer_id`, `opened_at`, `last_seen_at`, `ip`, `user_agent`, `state`, `otp_verified`.

3. `open.sign.otp.challenge` (optional)
- Fields: `request_signer_id`, `code_hash`, `expires_at`, `attempt_count`, `verified_at`.

4. `open.sign.portal.idempotency`
- Fields: `request_signer_id`, `endpoint`, `idempotency_key`, `request_hash`, `response_json`, `state`, `created_at`, `expires_at`.
- Purpose: deterministic response replay for duplicate submit/decline attempts and retry safety.

### Planned Folder Tree

```text
addons/open_sign_portal/
  __init__.py
  __manifest__.py
  security/
    ir.model.access.csv              # ACLs for optional portal session/OTP models
    open_sign_portal_security.xml    # Record rules for signer-scoped session/challenge access
  controllers/
    __init__.py
    portal_sign.py                   # signer routes and access-token handlers
  models/
    __init__.py
    sign_request_signer_portal.py    # portal.mixin extension and access URL helpers
    signing_session.py               # session tracking and replay controls
    otp_challenge.py                 # optional OTP challenge lifecycle
    portal_idempotency.py            # idempotency key registry and replay support
  views/
    portal_templates.xml             # signer portal pages
  data/
    mail_templates.xml               # portal-specific email templates
  tests/
    __init__.py
    test_portal_token_flow.py        # token validity + signer submission
    test_portal_security.py          # replay/expiry/revocation behavior
    test_portal_otp.py               # optional OTP verification path
    test_portal_idempotency.py       # duplicate submit/decline idempotent behavior
```

### Datatypes

- `TokenState`: `active`, `expired`, `revoked`, `consumed`.
- `PortalSubmitPayload`: signer values plus submit metadata.

---

## Addon Specification: `open_sign_certificate` (Optional)

### Interfaces

- Service API:
  - `certificate_service.sign_pdf(final_pdf_attachment_id, certificate_ref)`
  - `certificate_service.verify_pdf_signature(attachment_id)`
- Settings UI/API:
  - Certificate profile selection on request/template/company config.

### Database Entities

1. `open.sign.certificate.profile`
- Fields: `name`, `provider`, `key_ref`, `cert_ref`, `active`, `company_id`, `signing_algorithm`.

2. `open.sign.certificate.log`
- Fields: `request_id`, `profile_id`, `signed_attachment_id`, `signed_at`, `verification_status`, `details_json`.

### Planned Folder Tree

```text
addons/open_sign_certificate/
  __init__.py
  __manifest__.py
  models/
    __init__.py
    certificate_profile.py           # certificate profile model
    certificate_log.py               # signing and verification records
  services/
    __init__.py
    certificate_service.py           # sign_pdf(), verify_pdf_signature()
  views/
    certificate_profile_views.xml    # admin config views
  security/
    ir.model.access.csv
  tests/
    __init__.py
    test_certificate_signing.py      # optional module functional tests
```

### Datatypes

- `VerificationStatus`: `valid`, `invalid`, `unknown`, `error`.

---

## Database Storage Contract (Schema v1 Draft)

This section is the implementation baseline for persisted data. It is intentionally explicit for junior developers and must be treated as the source-of-truth contract for model creation, constraints, and migrations.

### Global ORM and SQL Conventions

- Implicit Odoo audit fields (`id`, `create_uid`, `create_date`, `write_uid`, `write_date`) exist on all models and are omitted below unless behavior depends on them.
- Use `check_company=True` on cross-company `Many2one` relationships where applicable.
- All `Many2one` foreign keys must declare an explicit `ondelete` policy.
- All business status fields are `Selection` and indexed.
- Add indexes for high-frequency lookup columns: `company_id`, `status/state`, `request_id`, `template_id`, `role_id`, `signer_id`, `expires_at`, `event_at`.
- Use `fields.Json` for structured payloads (`value_json`, `metadata_json`, `details_json`) and validate schema at service-layer boundaries.
- Model-level integrity that cannot be represented with SQL checks must be enforced with Python constraints and tested.
- Persist all datetime evidence values in UTC; timezone display conversions are presentation-only.
- Use SHA-256 hex digests for source/final artifact integrity fields and exported evidence package verification.
- Mutating portal transitions (`submit`, `decline`) must be protected by locking and idempotency-key checks.
- Requests must bind to an immutable template version before they can be sent.

### Core Domain Models (`open_sign`)

#### `open.sign.template`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `name` | `Char` | Yes | - | non-empty; indexed | Display name in backend, portal notifications |
| `state` | `Selection(draft,published,archived)` | Yes | - | default `draft`; indexed | Controls template availability in request creation |
| `source_attachment_id` | `Many2one(ir.attachment)` | Yes | FK, `ondelete='restrict'` | attachment mimetype must be PDF | Source document consumed by web editor and PDF mapper |
| `active` | `Boolean` | Yes | - | default `True`; indexed | Standard archive behavior |
| `company_id` | `Many2one(res.company)` | Yes | FK, `ondelete='restrict'` | indexed; company isolation enforced | ACL and record rules boundary |
| `owner_id` | `Many2one(res.users)` | Yes | FK, `ondelete='restrict'` | indexed | Operational ownership and filtering |
| `role_ids` | `One2many(open.sign.role, template_id)` | No | relation-only | not stored on this table | Drives signer-role assignment |
| `field_ids` | `One2many(open.sign.template.field, template_id)` | No | relation-only | not stored on this table | Drives signing payload structure |
| `version_ids` | `One2many(open.sign.template.version, template_id)` | No | relation-only | not stored on this table | Immutable snapshots available for request versioning |
| `request_ids` | `One2many(open.sign.request, template_id)` | No | relation-only | not stored on this table | Back-reference for usage and impact analysis |

Model constraints:
- Template publish does not require a signature-type field.
- Templates intended for request send flows must define at least one signer role before request version/send transitions.
- Archival of a template referenced by active requests is blocked by business rule.

#### `open.sign.template.version`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `template_id` | `Many2one(open.sign.template)` | Yes | FK, `ondelete='cascade'` | indexed | Parent template for lineage |
| `version_number` | `Integer` | Yes | - | `> 0`; indexed | Monotonic template version identifier |
| `source_attachment_id` | `Many2one(ir.attachment)` | Yes | FK, `ondelete='restrict'` | indexed | Frozen source document for this version |
| `source_pdf_sha256` | `Char` | Yes | - | fixed 64-char hex; indexed | Immutable digest for legal evidence |
| `field_snapshot_json` | `Json` | Yes | - | schema checked by service | Frozen field geometry/type/rule snapshot |
| `role_snapshot_json` | `Json` | Yes | - | schema checked by service | Frozen signer role snapshot |
| `published_at` | `Datetime` | Yes | - | indexed | Snapshot creation timestamp |
| `published_by` | `Many2one(res.users)` | Yes | FK, `ondelete='restrict'` | indexed | Actor who created version |
| `state` | `Selection(active,superseded)` | Yes | - | default `active`; indexed | Snapshot lifecycle metadata |

Model constraints:
- Unique template version number (`UNIQUE(template_id, version_number)`).
- Snapshot rows are immutable after creation (manager-only corrective migration scripts excepted).
- Snapshot digest and source attachment must remain consistent for the full lifecycle.

#### `open.sign.role`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `template_id` | `Many2one(open.sign.template)` | Yes | FK, `ondelete='cascade'` | indexed | Parent template |
| `name` | `Char` | Yes | - | non-empty | Displayed as signer role label |
| `name_normalized` | `Char` | Yes | - | indexed; normalized key | Internal case-insensitive uniqueness key |
| `sequence` | `Integer` | Yes | - | default `10`; indexed | Used for ordered signing and UI ordering |
| `required` | `Boolean` | Yes | - | default `True` | Optional signer slots supported when false |
| `color` | `Integer` | No | - | default `0` | Editor/preview color coding |

Model constraints:
- Role names are trim-normalized and unique per template using case-insensitive comparison (`UNIQUE(template_id, name_normalized)`).
- Sequence must be non-negative.

#### `open.sign.template.field`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `template_id` | `Many2one(open.sign.template)` | Yes | FK, `ondelete='cascade'` | indexed | Parent template |
| `role_id` | `Many2one(open.sign.role)` | Yes | FK, `ondelete='restrict'` | indexed | Field ownership by signer role |
| `type` | `Selection(FieldType)` | Yes | - | indexed | Validation and widget rendering branch |
| `label` | `Char` | Yes | - | non-empty | Display label in editor/portal |
| `required` | `Boolean` | Yes | - | default `False` | Enforced in client and server validation |
| `page` | `Integer` | Yes | - | `>= 1`; indexed | PDF page binding |
| `x` | `Float` | Yes | - | `0 <= x <= 1` | Normalized coordinate for renderer/editor |
| `y` | `Float` | Yes | - | `0 <= y <= 1` | Normalized coordinate for renderer/editor |
| `width` | `Float` | Yes | - | `0 < width <= 1` | Overlay size and flattened output size |
| `height` | `Float` | Yes | - | `0 < height <= 1` | Overlay size and flattened output size |
| `sequence` | `Integer` | Yes | - | default `10`; indexed | Deterministic presentation order |
| `default_value` | `Text` | No | - | - | Initial field content |
| `validation_regex` | `Char` | No | - | valid regex if set | Optional advanced validation |
| `min_length` | `Integer` | No | - | `>= 0` when set | Text-length lower bound |
| `max_length` | `Integer` | No | - | `>= min_length` when both set | Text-length upper bound |
| `option_ids` | `One2many(open.sign.template.field.option, field_id)` | No | relation-only | not stored on this table | Required for `radio` and `selection` types |

Model constraints:
- `role_id.template_id` must match `template_id`.
- `radio` and `selection` field types require options.
- Non-option field types must not have option rows.

#### `open.sign.template.field.option`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `field_id` | `Many2one(open.sign.template.field)` | Yes | FK, `ondelete='cascade'` | indexed | Parent field |
| `value` | `Char` | Yes | - | non-empty | Stored canonical value in submissions |
| `label` | `Char` | Yes | - | non-empty | UI label for option |
| `sequence` | `Integer` | Yes | - | default `10`; indexed | Deterministic display ordering |
| `is_default` | `Boolean` | Yes | - | default `False` | Preselected option in editor/signer UI |

Model constraints:
- Unique option value per field (`UNIQUE(field_id, value)`).
- At most one default option per field (Python constraint).

#### `open.sign.request`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `name` | `Char` | Yes | - | default from sequence; indexed | Primary human identifier |
| `template_id` | `Many2one(open.sign.template)` | Yes | FK, `ondelete='restrict'` | indexed | Source template for signer/value expansion |
| `template_version_id` | `Many2one(open.sign.template.version)` | No | FK, `ondelete='restrict'` | indexed | Immutable template snapshot bound before send |
| `status` | `Selection(RequestStatus)` | Yes | - | default `draft`; indexed | Workflow engine and UI state |
| `sent_at` | `Datetime` | No | - | indexed | Transition evidence (`versioned` to `sent`) |
| `completed_at` | `Datetime` | No | - | indexed | Completion and retention baseline |
| `expires_at` | `Datetime` | No | - | indexed | Expiration checks by cron and portal |
| `final_attachment_id` | `Many2one(ir.attachment)` | No | FK, `ondelete='restrict'` | indexed | Final flattened signed artifact |
| `source_pdf_sha256` | `Char` | No | - | fixed 64-char hex; indexed | Immutable digest of bound template version source PDF |
| `final_pdf_sha256` | `Char` | No | - | fixed 64-char hex; indexed | Immutable digest of final signed PDF |
| `owner_id` | `Many2one(res.users)` | Yes | FK, `ondelete='restrict'` | indexed | Operational ownership |
| `company_id` | `Many2one(res.company)` | Yes | FK, `ondelete='restrict'` | indexed | Multi-company boundary |
| `ordered_signing` | `Boolean` | Yes | - | default `True` | Controls sequential vs parallel signer gating |
| `evidence_schema_version` | `Char` | Yes | - | default `v1`; indexed | Export/evidence compatibility marker |
| `lock_version` | `Integer` | Yes | - | default `0`; indexed | Optimistic concurrency guard for portal writes |
| `signed_count` | `Integer` (computed, stored) | No | - | indexed | Fast dashboard and state decisions |
| `pending_count` | `Integer` (computed, stored) | No | - | indexed | Fast dashboard and reminders |
| `declined_count` | `Integer` (computed, stored) | No | - | indexed | Decline workflow visibility |
| `last_event_at` | `Datetime` (computed, stored) | No | - | indexed | Activity sorting and monitoring |

Model constraints:
- Status transitions must follow the approved transition matrix.
- Any status at or beyond `versioned` requires `template_version_id` and `source_pdf_sha256`.
- Transition to `sent` requires at least one signer (`open.sign.request.signer`) on the request.
- `template_version_id.template_id` must equal `template_id`.
- `source_pdf_sha256` must equal `template_version_id.source_pdf_sha256` when `template_version_id` is set.
- `completed` status requires `completed_at` and `final_attachment_id`.
- `completed` status requires `final_pdf_sha256`.
- Signature-type fields are optional; completion gating relies on required-field validation and consent evidence policy.
- `expires_at` must be greater than or equal to `sent_at` when both exist.

#### `open.sign.request.signer`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `request_id` | `Many2one(open.sign.request)` | Yes | FK, `ondelete='cascade'` | indexed | Parent request |
| `partner_id` | `Many2one(res.partner)` | No | FK, `ondelete='set null'` | indexed | Optional linked contact |
| `email` | `Char` | Yes | - | normalized email format; indexed | Invitation target and identity anchor |
| `role_id` | `Many2one(open.sign.role)` | Yes | FK, `ondelete='restrict'` | indexed | Template role resolution |
| `sequence` | `Integer` | Yes | - | default `10`; indexed | Ordered signing gating |
| `state` | `Selection(SignerState)` | Yes | - | default `pending`; indexed | Signer lifecycle tracking |
| `signed_at` | `Datetime` | No | - | indexed | Signature timestamp evidence |
| `declined_reason` | `Text` | No | - | - | Decline explanation |
| `last_opened_at` | `Datetime` | No | - | indexed | Portal engagement evidence |
| `ip_last` | `Char` | No | - | sized for IPv4/IPv6 | Last-seen signer IP snapshot |
| `consent_accepted_at` | `Datetime` | No | - | indexed | Legal consent timestamp |
| `consent_text_hash` | `Char` | No | - | hash format and length check | Binds action to presented legal text |
| `signer_timezone` | `Char` | No | - | valid TZ identifier when set | Evidence rendering and UX |
| `access_token` | `Char` (from `portal.mixin`) | No | - | indexed | Tokenized portal signer access |

Model constraints:
- Unique signer role per request (`UNIQUE(request_id, role_id)`).
- `state='signed'` requires `signed_at`.
- `role_id.template_id` must equal `request_id.template_id`.

#### `open.sign.request.value`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `request_id` | `Many2one(open.sign.request)` | Yes | FK, `ondelete='cascade'` | indexed | Parent request |
| `template_field_id` | `Many2one(open.sign.template.field)` | Yes | FK, `ondelete='restrict'` | indexed | Field definition source |
| `signer_id` | `Many2one(open.sign.request.signer)` | Yes | FK, `ondelete='cascade'` | indexed | Signer submitting value |
| `value_text` | `Text` | No | - | - | Scalar/string representation |
| `value_json` | `Json` | No | - | schema checked by validator | Structured payload for complex types |
| `signed_payload_attachment_id` | `Many2one(ir.attachment)` | No | FK, `ondelete='set null'` | indexed | Upload payloads (signature image/stamp) |
| `is_valid` | `Boolean` | Yes | - | default `False`; indexed | Validation gate for submit/finalize |

Model constraints:
- Unique value slot per `(request_id, template_field_id, signer_id)`.
- `template_field_id.template_id` must match `request_id.template_id`.
- `signer_id.request_id` must match `request_id`.
- `signer_id.role_id` must match `template_field_id.role_id`.

#### `open.sign.audit.log`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `request_id` | `Many2one(open.sign.request)` | Yes | FK, `ondelete='cascade'` | indexed | Parent request |
| `signer_id` | `Many2one(open.sign.request.signer)` | No | FK, `ondelete='set null'` | indexed | Actor context when signer-driven |
| `event_type` | `Selection(AuditEventType)` | Yes | - | indexed | Canonical audit event code |
| `event_sequence` | `Integer` | Yes | - | indexed | Monotonic request-local event ordering |
| `event_at` | `Datetime` | Yes | - | default now; indexed | Event timestamp |
| `ip` | `Char` | No | - | sized for IPv4/IPv6 | Network evidence |
| `user_agent` | `Char` | No | - | - | Device/browser evidence |
| `metadata_json` | `Json` | No | - | schema checked by audit service | Event metadata payload |
| `hash_chain` | `Char` | Yes | - | indexed; unique per request | Tamper-evidence hash |
| `previous_hash` | `Char` | No | - | - | Hash-chain link |
| `consent_text_hash` | `Char` | No | - | hash format/length check | Legal text evidence linkage |

Model constraints:
- `UNIQUE(request_id, hash_chain)`.
- `UNIQUE(request_id, event_sequence)`.
- Append-only behavior once request is `completed` or `voided` (no update/delete except privileged repair tooling).
- `previous_hash` continuity enforced by audit service logic.

### Portal Hardening Models (`open_sign_portal`)

#### `open.sign.signing.session` (optional hardening)

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `request_signer_id` | `Many2one(open.sign.request.signer)` | Yes | FK, `ondelete='cascade'` | indexed | Session owner signer |
| `opened_at` | `Datetime` | Yes | - | default now; indexed | Session start evidence |
| `last_seen_at` | `Datetime` | Yes | - | indexed | Idle/replay policy enforcement |
| `ip` | `Char` | No | - | sized for IPv4/IPv6 | Session context |
| `user_agent` | `Char` | No | - | - | Session context |
| `state` | `Selection(open,submitted,expired,revoked)` | Yes | - | default `open`; indexed | Session validity |
| `otp_verified` | `Boolean` | Yes | - | default `False`; indexed | Optional OTP gate state |

Model constraints:
- Maximum one active `open` session per signer (Python constraint).
- Submitted/expired/revoked sessions become read-only.

#### `open.sign.otp.challenge` (optional)

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `request_signer_id` | `Many2one(open.sign.request.signer)` | Yes | FK, `ondelete='cascade'` | indexed | Challenge owner signer |
| `code_hash` | `Char` | Yes | - | fixed hash format and length | Never store raw OTP |
| `expires_at` | `Datetime` | Yes | - | indexed | Challenge expiration gate |
| `attempt_count` | `Integer` | Yes | - | default `0`; `>= 0` | Brute-force protection counter |
| `verified_at` | `Datetime` | No | - | indexed | Verification evidence |

Model constraints:
- One non-expired, non-verified challenge per signer (Python constraint).
- `attempt_count` hard limit enforced in service/controller layer.

#### `open.sign.portal.idempotency`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `request_signer_id` | `Many2one(open.sign.request.signer)` | Yes | FK, `ondelete='cascade'` | indexed | Idempotency scope owner |
| `endpoint` | `Selection(save,submit,decline)` | Yes | - | indexed | Endpoint-specific key scope |
| `idempotency_key` | `Char` | Yes | - | non-empty; indexed | Client-provided retry key (UUID expected) |
| `request_hash` | `Char` | Yes | - | fixed hash format | Payload fingerprint for conflict detection |
| `response_json` | `Json` | No | - | - | Stored deterministic response payload |
| `state` | `Selection(in_progress,completed,failed)` | Yes | - | default `in_progress`; indexed | Lifecycle of key processing |
| `created_at` | `Datetime` | Yes | - | default now; indexed | Creation timestamp |
| `expires_at` | `Datetime` | Yes | - | indexed | Cleanup and replay window control |

Model constraints:
- Unique key per signer endpoint (`UNIQUE(request_signer_id, endpoint, idempotency_key)`).
- Same key with different `request_hash` must return `idempotency_conflict`.

### Certificate Models (`open_sign_certificate`, optional)

#### `open.sign.certificate.profile`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `name` | `Char` | Yes | - | non-empty; indexed | Admin-facing profile identifier |
| `provider` | `Selection` | Yes | - | indexed | Controls signing backend implementation |
| `key_ref` | `Char` | Yes | - | non-empty | Key material reference (not raw key) |
| `cert_ref` | `Char` | Yes | - | non-empty | Certificate reference |
| `active` | `Boolean` | Yes | - | default `True`; indexed | Operational toggle |
| `company_id` | `Many2one(res.company)` | Yes | FK, `ondelete='restrict'` | indexed | Company isolation |
| `signing_algorithm` | `Selection` | Yes | - | indexed | Algorithm policy enforcement |

Model constraints:
- Unique profile name per company.
- Secret values are references only; private keys must never be stored inline in this model.

#### `open.sign.certificate.log`

| Field | Odoo Type | Required | FK / On Delete | Constraints and Index | Interaction Notes |
|---|---|---|---|---|---|
| `request_id` | `Many2one(open.sign.request)` | Yes | FK, `ondelete='cascade'` | indexed | Signed request context |
| `profile_id` | `Many2one(open.sign.certificate.profile)` | Yes | FK, `ondelete='restrict'` | indexed | Certificate profile used |
| `signed_attachment_id` | `Many2one(ir.attachment)` | Yes | FK, `ondelete='restrict'` | indexed | Cryptographically signed PDF |
| `signed_at` | `Datetime` | Yes | - | indexed | Signing timestamp evidence |
| `verification_status` | `Selection(VerificationStatus)` | Yes | - | indexed | Verification outcome |
| `details_json` | `Json` | No | - | schema checked by service | Verification details and diagnostics |

Model constraints:
- Unique pair `(request_id, signed_attachment_id)`.
- Verification events append to logs, not overwrite prior evidence.

### XML-Loaded Persistent Records (Non-Business Schema)

The addon set also persists configuration and metadata records via XML/CSV files. These are not business transaction models but are part of system behavior and must be tracked:

| Record Type | Source Files | Critical Fields | Purpose |
|---|---|---|---|
| `res.groups` | `security/open_sign_groups.xml` | `name`, `implied_ids`, `privilege_id` | Security role definitions |
| `res.groups.privilege` | `security/open_sign_groups.xml` | `name`, `category_id`, `sequence` | Privilege grouping for security roles |
| `ir.model.access` | `security/ir.model.access.csv` (each addon) | `model_id`, `group_id`, CRUD flags | Model access control |
| `ir.rule` | `security/open_sign_security.xml`, `security/open_sign_portal_security.xml` | `domain_force`, `groups` | Multi-company and ownership boundaries |
| `mail.template` | `data/mail_templates.xml` | `model_id`, `subject`, `body_html` | Invitation/reminder/completion notices |
| `ir.cron` | `data/ir_cron.xml` | `model_id`, `code`, `interval_*` | Reminder and expiration jobs |
| `ir.sequence` | `data/sequence.xml` | `code`, `prefix`, `padding` | Request numbering |
| `ir.ui.view` | `views/*.xml`, `report/*.xml` | `model`, `arch`, `inherit_id` | Backend, portal, and report rendering |

## Development Task Breakdown and Tracking

Legend:

- `[ ]` Not started
- `[~]` In progress
- `[x]` Completed

### Phase 0: Planning and Architecture

- [x] `T00` Create and baseline `FEATURE.md` control document.
- [x] `T01` Confirm Odoo target version and compatibility constraints.
- [x] `T02` Finalize addon names, dependencies, and install order.
- [x] `T03` Define legal/compliance acceptance criteria (audit, retention, consent).
- [x] `T04` Approve wireframes for template editor and signer portal.
- [x] `T05` Decide PDF processing stack and licensing constraints.
- [x] `T06` Finalize status transition matrix, ACL matrix, and cross-model invariants from the schema contract.
- [x] `T07` Define evidence retention, archival, and purge policy.
- [x] `T08` Define observability baseline (events, metrics, alerts).
- [x] `T09` Finalize Odoo compliance checklist (lint, module structure, route/model conventions, XML `noupdate`/external-ID policy).
- [x] `T90` Complete Odoo design data collection notes using the reference map.
- [x] `T91` Create task cards (template-based) for all remaining open tasks.
- [x] `T92` Add PR template/checklist section for this feature in team workflow docs.
- [x] `T93` Create developer command cookbook for local setup, test, and lint flows.
- [x] `T94` Finalize security group/ACL matrix and model-level access policy.
- [x] `T95` Finalize portal endpoint contract and error-code policy.
- [x] `T96` Finalize legal disclosure text strategy and consent evidence format.
- [x] `T97` Finalize signed attachment access policy (token scope, expiry, visibility).
- [x] `T98` Finalize field-type validation and normalization matrix with test vectors.
- [x] `T99` Finalize audit event taxonomy and evidence package schema v1.

### Phase 1: Core Addon (`open_sign`)

- [x] `T10` Scaffold addon with manifest/init/security skeleton.
- [x] `T11` Implement `open.sign.template` model + views.
- [x] `T12` Implement `open.sign.role` model + assignment flows.
- [x] `T13` Implement `open.sign.template.field` + `open.sign.template.field.option`.
- [x] `T14` Implement `open.sign.request` model + status engine.
- [x] `T15` Implement `open.sign.request.signer` with sequence logic.
- [x] `T16` Implement `open.sign.request.value` storage and normalization.
- [x] `T17` Implement `open.sign.audit.log` immutable records.
- [x] `T18` Implement validation service for required/optional and field-type checks (including signer evidence fields: `consent_text_hash`, `signer_timezone`, `ip_last` format validation).
- [x] `T19` Create base backend menus and form/tree/kanban views.
- [x] `T110` Add SQL constraints, FK `ondelete` policies, and indexes per schema contract.
- [x] `T111` Implement cron jobs for reminders and expiration.
- [x] `T112` Add core migration hooks and upgrade scripts aligned to schema contract evolution.
- [x] `T113` Implement security groups + ACL/record-rule matrix from design baseline.

### Phase 2: Web Editor Addon (`open_sign_web`)

- [x] `T20` Scaffold addon and declare backend/frontend assets in `__manifest__.py`.
- [x] `T21` Build template canvas with drag/drop/resizing on PDF pages.
- [x] `T22` Build field palette and field property editor.
- [x] `T23` Implement signer role assignment in editor.
- [x] `T24` Implement client-side value validation aligned with server rules.
- [x] `T25` Implement signature adoption dialog (draw/type/upload).
- [x] `T26` Add JS tests for geometry and validation payloads, including explicit frontend test-runner/discovery wiring so `/open_sign_web` test tags execute non-zero tests in CI.

### Phase 3: Portal Addon (`open_sign_portal`)

- [x] `T30` Scaffold addon with controller/routes and portal templates.
- [x] `T31` Extend signer model with `portal.mixin` and standard access-token URL flow.
- [x] `T32a` Harden signer portal access/session rules with a separate internal preview route, signer-only session mutation, and signer-facing request-state gating.
- [x] `T32b` Make portal save/submit flows atomic with savepoint-backed rollback on handled errors and lock/revision guards.
- [x] `T32c` Bind portal rendering/validation to immutable request-version snapshots, including legacy snapshot fallback and fail-closed contract handling.
- [x] `T32d` Clean up portal field serialization/evidence semantics, add regression coverage, and complete T32 closeout review.
- [x] `T32` Implement signing session open/save/submit flows, including explicit signer-action auth policy for token-based access vs authenticated internal fallback on save/submit endpoints.
- [x] `T33` Enforce signer order (sequential and parallel policies).
- [x] `T34` Implement decline flow and reason capture.
- [x] `T35` Add reminder/invitation/completion notifications, and make portal token URL generation the canonical source for resend/copy-link/invitation/reminder/completion flows.
- [x] `T36` Add portal security tests for replay and token abuse.
- [x] `T37` Implement optional OTP verification flow.
- [x] `T38` Implement endpoint response envelope/error codes and contract tests.
- [ ] `T39` Add portal addon ACL/rules (`security/ir.model.access.csv`, portal model record rules) for session/OTP models.
- [ ] `T316` Implement idempotency-key handling and concurrency-safe locking for submit/decline.
- [ ] `T317` Add duplicate-submit and race-condition test coverage for portal signer flows.
- [ ] `T310` Define and document external email-signer token strategy (reuse `portal.mixin` token flow vs signed/expiring payloads), including accepted link-sharing risk and compensating controls.
- [ ] `T311` Implement email-invitation magic-link issuance for email-only signers with resend rotation and explicit token revocation hooks.
- [ ] `T312` Implement public token entry and signer-context resolution for email-only signers without email-based ACL authorization.
- [ ] `T313` Implement token lifecycle hardening for email-only signers (expiry, revoke, replay handling, invalid-attempt throttling, and deterministic error codes).
- [ ] `T314` Extend audit/evidence taxonomy for email-token events (`token_issued`, `token_opened`, `token_rejected`, `token_revoked`) with export coverage.
- [ ] `T315` Add end-to-end and denial-path tests for email-only signer flow (tampered/expired/revoked token, spoofed email no-access, replay, and controlled link-sharing behavior).

### Phase 4: PDF Finalization and Audit Evidence

- [ ] `T40` Implement value-to-PDF rendering/flattening.
- [ ] `T41` Generate final signed attachment and lock request edits.
- [ ] `T42` Build completion certificate/evidence summary page.
- [ ] `T43` Extend audit logging with hash-chain integrity checks.
- [ ] `T44` Add end-to-end tests from send -> sign -> complete.
- [ ] `T45` Add audit package export (values, timeline, metadata).
- [ ] `T46` Persist consent/legal snapshot and include it in audit package output.
- [ ] `T47` Apply tokenized access policy for generated signed artifacts and payload attachments.
- [ ] `T410` Implement UTC timestamp trust policy checks and include clock metadata in evidence export.
- [ ] `T411` Persist source/final PDF SHA-256 digests and verify during evidence export.

### Phase 5: Certificate Module (`open_sign_certificate`) Optional

- [ ] `T50` Scaffold optional addon and profile models.
- [ ] `T51` Implement PDF certificate signing service.
- [ ] `T52` Implement signature verification and persisted results.
- [ ] `T53` Add admin configuration views and access control.
- [ ] `T54` Add optional integration tests.

### Phase 6: Hardening, QA, and Release

- [ ] `T60` Performance test with large PDFs and multi-signer load.
- [ ] `T61` Security review (token handling, PII, permission boundaries).
- [ ] `T62` Accessibility and mobile signing UX validation.
- [ ] `T63` Regression suite and CI integration.
- [ ] `T64` Prepare deployment/migration and operator runbook.
- [ ] `T65` UAT signoff and release checklist completion.
- [ ] `T66` Add observability dashboards and failure alerts.
- [ ] `T67` Execute backup/restore and failure-recovery validation.
- [ ] `T68` Run data retention and purge dry-run verification.
- [ ] `T69` Run lint/conformance checks (`test_lint` subset, manifest and module structure checks).
- [x] `T610` Run recurring hardening re-audit on completed tasks using the closeout checklist (server-authority fields, action preconditions, denial-path tests, UI/server alignment) and file follow-up fixes.

## Requirement Traceability Matrix

| Requirement | Tasks | Addon | Validation |
|---|---|---|---|
| `R-001` | `T11`, `T21`, `T40` | `open_sign`, `open_sign_web` | Unit + E2E tests |
| `R-002` | `T13`, `T24`, `T44` | `open_sign`, `open_sign_web` | Field-type test suite |
| `R-003` | `T18`, `T24`, `T44` | `open_sign`, `open_sign_web` | Server/client validation tests |
| `R-004` | `T12`, `T15`, `T33`, `T44` | `open_sign`, `open_sign_portal` | Workflow tests |
| `R-005` | `T25`, `T32`, `T44` | `open_sign_web`, `open_sign_portal` | UI + submit tests |
| `R-006` | `T06`, `T14`, `T43`, `T44` | `open_sign` | State transition tests |
| `R-007` | `T17`, `T43`, `T61`, `T314` | `open_sign`, `open_sign_portal` | Audit integrity + security review |
| `R-008` | `T40`, `T41`, `T44`, `T411` | `open_sign` | PDF output validation |
| `R-009` | `T31`, `T32`, `T36`, `T310`, `T311`, `T312`, `T313`, `T315` | `open_sign_portal` | Portal security tests |
| `R-010` | `T50`, `T51`, `T52` | `open_sign_certificate` | Signature verification tests |
| `R-011` | `T06`, `T94`, `T113`, `T61` | `open_sign`, `open_sign_portal` | ACL and multi-company rule tests |
| `R-012` | `T06`, `T14`, `T44` | `open_sign` | Invalid transition tests |
| `R-013` | `T07`, `T45`, `T68` | `open_sign` | Retention and export checks |
| `R-014` | `T112`, `T64`, `T63` | All | Upgrade test plan |
| `R-015` | `T08`, `T66` | All | Event/metric checks |
| `R-016` | `T37`, `T36`, `T61` | `open_sign_portal` | OTP and abuse tests |
| `R-017` | `T09`, `T20`, `T69` | All | Lint and structure compliance checks |
| `R-018` | `T91`, `T92`, `T93`, `T610`, `T65` | All | Review process audit |
| `R-019` | `T90`, `T05`, `T06` | All | Referenced design evidence in PRs |
| `R-020` | `T39`, `T94`, `T113`, `T61` | `open_sign`, `open_sign_portal` | ACL/rule matrix and access-boundary tests |
| `R-021` | `T95`, `T38`, `T36`, `T316`, `T317`, `T313`, `T315` | `open_sign_portal` | Endpoint contract and abuse/replay tests |
| `R-022` | `T03`, `T96`, `T46` | `open_sign`, `open_sign_portal` | Consent evidence persistence and export checks |
| `R-023` | `T97`, `T47`, `T36` | `open_sign`, `open_sign_portal` | Tokenized artifact access and security tests |
| `R-024` | `T95`, `T316`, `T317`, `T38`, `T36` | `open_sign_portal` | Idempotency and race-condition tests |
| `R-025` | `T08`, `T410`, `T61` | `open_sign`, `open_sign_portal` | UTC timestamp and drift-control validation |
| `R-026` | `T98`, `T16`, `T18`, `T24`, `T44` | `open_sign`, `open_sign_web` | Validation matrix conformance tests |
| `R-027` | `T99`, `T42`, `T45`, `T63` | `open_sign` | Evidence schema and event taxonomy checks |
| `R-028` | `T40`, `T41`, `T411`, `T45` | `open_sign` | Artifact digest integrity verification |
| `R-029` | `T12`, `T14`, `T15`, `T44` | `open_sign`, `open_sign_portal` | Participant-required flow tests without mandatory signature field |

## Milestones and Exit Criteria

| Milestone | Target | Exit Criteria |
|---|---|---|
| `M0` Design Freeze | `2026-02-26 (Complete)` | `T01`-`T09`, `T90`-`T99` complete, ADRs updated |
| `M1` Core Backend | `Complete (2026-03-01)` | `T10`-`T19`, `T110`-`T113` complete + tests green |
| `M2` Editor UX | TBD | `T20`-`T26` complete + demo approved |
| `M3` Portal Signing | TBD | `T30`-`T39`, `T310`-`T317` complete + security baseline pass |
| `M4` PDF + Audit | TBD | `T40`-`T47`, `T410`-`T411` complete + E2E pass |
| `M5` Certificate (Optional) | TBD | `T50`-`T54` complete + verification pass |
| `M6` Release | TBD | `T60`-`T69` complete + UAT signoff |

## Risks and Mitigations

| Risk ID | Risk | Severity | Mitigation | Owner | Status |
|---|---|---|---|---|---|
| `RK-001` | PDF rendering inconsistencies across viewers | High | Validate with multiple PDF libraries/viewers, add golden tests | Backend | Open |
| `RK-002` | Token leakage or replay attacks | High | Use `portal.mixin` tokens with strict expiry/revocation policy, optional OTP, replay tests | Security | Open |
| `RK-003` | Field coordinate drift on responsive layouts | Medium | Normalize coordinates and fixed PDF viewport mapping | Frontend | Open |
| `RK-004` | Legal expectations exceed MVP evidence model | High | Early legal review and explicit compliance baseline | Product | Open |
| `RK-005` | Certificate support complexity impacts timeline | Medium | Keep addon optional and behind milestone gate | Engineering | Open |
| `RK-006` | PDF/certificate dependency licensing incompatibility | Medium | License review at `T05`; pin approved libraries only | Engineering | Open |
| `RK-007` | Missing migration scripts causes upgrade regressions | High | Implement `T112` and upgrade tests in CI | Backend | Mitigated (`T112` complete; keep CI upgrade coverage active) |
| `RK-008` | Retention/purge process removes evidence prematurely | High | Controlled policy, dry-run mode, audit on purge events | Ops/Product | Open |
| `RK-009` | Addon diverges from Odoo lint/convention expectations | Medium | Track `T09` + `T69`, enforce review checklist in PRs | Engineering | Open |
| `RK-010` | Junior implementation diverges from intended architecture | High | Enforce task card + PR checklist + code reference evidence (`T90`-`T92`) | Engineering | Open |
| `RK-011` | Portal endpoint contract drifts between frontend and backend | Medium | Lock v1 contract in `T95`, enforce contract tests in `T38` | Web/Backend | Open |
| `RK-012` | Consent evidence is incomplete or unverifiable during audit/export | High | Persist consent hash/timestamp in `T46` and validate in security review `T61` | Product/Security | Open |
| `RK-013` | Signed artifacts become accessible outside token scope | High | Enforce tokenized attachment policy in `T97`/`T47` and test abuse paths in `T36` | Security/Backend | Open |
| `RK-014` | Duplicate submits or concurrent requests create inconsistent signer/request states | High | Implement idempotency + locking (`T316`) and race tests (`T317`) | Backend/Security | Open |
| `RK-015` | Server clock drift undermines timestamp credibility in legal evidence | High | Define UTC clock policy and drift checks (`T410`) plus operational monitoring | Platform/Ops | Open |
| `RK-016` | Missing or mismatched artifact digests weakens integrity proof during disputes | High | Persist and verify SHA-256 digests (`T411`) in evidence export flow | Backend | Open |
| `RK-017` | Email-only signer magic links are forwarded/shared, allowing non-intended recipients to sign | High | Explicitly accept baseline risk, enforce short TTL + revoke/rotate controls (`T311`-`T313`), log token events (`T314`), and optionally require OTP (`T37`) for higher-assurance profiles | Product/Security | Open |

## Definition of Done (DoD)

A task may be marked complete only if:

- Code merged with tests.
- Security and access rules verified where applicable.
- Action precondition guards and denial-path tests are present for all new stateful or security-sensitive behavior.
- A comprehensive post-change review has been completed after coding (intent vs implementation, cross-scope impact, and regression risk), with findings resolved or explicitly documented.
- Relevant requirement IDs referenced in PR.
- For feature branches: `FEATURE.md` task status and change log updated (for non-feature branches, linked task/issue and gate evidence provided).
- Documentation updated for any user-visible behavior change.
- PR includes links to the Odoo reference files used for design decisions.
- No known critical defects for the task scope.

## Odoo Compliance Checklist (Per PR)

Use this checklist in every implementation PR touching this feature:

- [ ] Manifest keys/values conform to Odoo expectations (`test_manifests` equivalent checks).
- [ ] `__init__.py` exists for module and test packages; all tests are imported in `tests/__init__.py`.
- [ ] No direct `odoo.orm` imports.
- [ ] Public method signatures avoid `ids`/`context` parameter names.
- [ ] Method overrides preserve parent signature/decorators where required.
- [ ] One2many inverse Many2one fields are indexed appropriately (`btree`/`btree_not_null` where needed).
- [ ] Persisted model changes align with the `Database Storage Contract (Schema v1 Draft)` section.
- [ ] Security reviewed: ACL + record rules + portal access token checks.
- [ ] Comprehensive post-change review completed after final code edits (whole-scope behavior, security boundaries, and regression scan), not only incremental checks during implementation.
- [ ] Server-authoritative fields are protected in model layer; client-submitted lifecycle/evidence/status writes are rejected unless explicitly allowed.
- [ ] Stateful actions enforce business preconditions (including actionable participants, not just row existence).
- [ ] Denial-path tests cover tamper attempts and invalid transitions for the changed scope.
- [ ] UI writeability (`readonly`/invisible) is aligned with server authority for sensitive fields.
- [ ] `jsonrpc` endpoints follow documented request/response/error envelope contract.
- [ ] Mutating portal endpoints enforce idempotency keys and race-safe transition handling.
- [ ] Evidence timestamps are UTC and artifact digest fields are generated/verified as specified.
- [ ] Signed artifacts and attachment payloads enforce token scope and expiry checks.
- [ ] JS translation usage follows `_t` conventions and avoids `_('...')`.
- [ ] Assets declared in manifest and tests wired through `web.assets_tests` / `web.assets_unit_tests`.

## Developer Command Cookbook (Starter)

Use these command patterns during development (adapt database/module names as needed):

```bash
# Upgrade/install target modules
./odoo-bin -d <db_name> -u open_sign,open_sign_web,open_sign_portal --stop-after-init

# Run Python tests for target modules
./odoo-bin -d <db_name> --test-enable --test-tags /open_sign,/open_sign_portal --stop-after-init

# Run a focused test class
./odoo-bin -d <db_name> --test-enable --test-tags open_sign.tests.test_sign_request_flow --stop-after-init

# Run frontend tours/unit tests (module-specific tags/assets)
./odoo-bin -d <db_name> -u open_sign_web --test-enable --test-tags /open_sign_web --stop-after-init
```

Notes:

- Always run module upgrade before functional testing after schema changes.
- Prefer focused test tags while iterating; run broader test scope before merge.

## Progress Snapshot

Counts below track only `T*` development tasks in the phase task board.

- Completed tasks: `37`
- In progress tasks: `0`
- Remaining tasks: `48`

## Update Log

| Date | Author | Update |
|---|---|---|
| `2026-02-26` | Codex | Created initial feature plan, design controls, addon specs, and task tracking baseline. |
| `2026-02-26` | Codex | Applied review updates: control requirements, missing entities, transition matrix, dependency corrections, expanded task board. |
| `2026-02-26` | Codex | Added Odoo codebase alignment rules, switched portal token strategy to `portal.mixin`, and aligned module/test/assets structure with repository conventions. |
| `2026-02-26` | Codex | Added junior-focused delivery scaffolding (DoR, task card template, PR checklist), reference study map, and developer command cookbook. |
| `2026-02-26` | Codex | Renamed planned addon/model namespace from `custom_*` / `custom.*` to `open_*` / `open.*` across the feature plan. |
| `2026-02-26` | Codex | Completed final comprehensive review updates: added `R-020`-`R-023` traceability rows, milestone gate alignment, additional risk controls, and corrected progress metrics. |
| `2026-02-26` | Codex | Added concept coverage re-review and detailed schema storage contract with field types, FK/ondelete policies, constraints, and component interaction notes. |
| `2026-02-26` | Codex | Compared official addon data patterns and added explicit model-vs-XML guidance, manifest load plan, and portal addon security artifacts/tasks. |
| `2026-02-26` | Codex | Added senior hardening controls for idempotency/race safety, UTC timestamp trust policy, field validation taxonomy, evidence schema versioning, and immutable PDF digest tracking. |
| `2026-02-26` | Codex | Generated M0 deliverables bundle (`T90`-`T99`) under `doc/open_sign/m0/`, created task cards for remaining open tasks, and updated Open Sign PR checklist section. |
| `2026-02-26` | Codex | Applied Phase 0 decision updates (`T01/T02/T03/T06/T07`), added immutable template-version-before-send model/status flow, and added planning artifacts for wireframes, observability, merge gates, and PDF stack recommendation. |
| `2026-02-26` | Codex | Applied final M0 approvals (`T04/T05/T08/T09`), updated merge-gate policy for feature-branch-only `FEATURE.md` updates, and set M0 design freeze milestone target date. |
| `2026-02-26` | Codex | Closed M0 and opened M1 by scaffolding `T10` (`addons/open_sign` manifest/init/security skeleton), then updated milestone/progress tracking. |
| `2026-02-26` | Codex | Completed `T11` by implementing `open.sign.template` model, ACL entries, and initial backend views/menus for `open_sign`. |
| `2026-02-26` | Codex | Addressed T11 review findings by adding `open_sign` unit tests for template behavior and granting auditor menu visibility without changing write permissions. |
| `2026-02-27` | Codex | Completed `T12` by adding `open.sign.role` model integration, role management/action/menu views, template role assignment UI, and role constraint/assignment unit tests. |
| `2026-02-27` | Codex | Captured participant-vs-signature invariant: requests require at least one participant role/signer while signature fields are optional for acknowledgement workflows, and updated requirements/traceability/contracts accordingly. |
| `2026-02-27` | Codex | Strengthened T12 coverage with ACL behavior tests for `open.sign.role` (auditor read-only, user no-unlink, manager unlink) and aligned role-name normalization/uniqueness constraints. |
| `2026-02-27` | Codex | Hardened role-name uniqueness with DB-backed case-insensitive key (`name_normalized`) to close race-condition gaps and updated tests accordingly. |
| `2026-02-27` | Codex | Final T12 review sign-off completed (no additional in-scope blockers found), confirmed `T13` as next execution task, and refreshed continuation notes for handoff readiness. |
| `2026-02-27` | Codex | Completed `T13` by implementing `open.sign.template.field` and `open.sign.template.field.option` models, constraints, ACL rows, template field management views/menu, and dedicated field/option unit tests including ACL behavior coverage. |
| `2026-03-01` | Codex | Started Phase 2 by completing `T20`: scaffolded `open_sign_web` addon, declared backend/test assets, added initial OWL/JS/CSS skeleton files, and added baseline geometry/validation JS test stubs. |
| `2026-03-01` | Codex | Completed `T21` by implementing a usable `TemplateCanvas` OWL client action (drag/move/resize field overlays on page canvas), adding backend action/menu wiring for editor access, and validating install + `/open_sign` regression (`0 failed, 0 errors`); frontend test discovery remains explicitly tracked for `T26`. |
| `2026-03-01` | Codex | Applied T21 security hardening follow-up: restricted `open_sign_web` Editor menu visibility to `open_sign.group_open_sign_user` (auditor removed), and revalidated `open_sign_web` module load plus `/open_sign` regression stability. |
| `2026-03-01` | Codex | Completed `T22` by implementing a working field palette and property editor in `open_sign_web` (typed field insertion + editable metadata panel with client-side normalization), and revalidated module load plus `/open_sign` regression (`0 failed, 0 errors`); frontend test execution wiring remains deferred to `T26`. |
| `2026-03-01` | Codex | Applied `T22` hardening follow-up from review findings: JS-translated palette labels (`_t`), deterministic unknown-type fallback to `text`, and explicit backend-safe field serialization helper (`toTemplateFieldVals`) to keep editor-only properties out of ORM payloads until schema support exists. |
| `2026-03-01` | Codex | Completed `T22` #4 follow-up by wiring backend-safe serialization into the canvas flow (`serializeTemplateFieldsForBackend` using `toTemplateFieldVals`) and adding regression coverage proving editor-only keys (`placeholder`, `helpText`) are excluded from backend payloads. |
| `2026-02-28` | Codex | Closed out `T13` with Odoo 19 compatibility fixes (groups privilege model, view XML updates, constraint API updates), removed deprecated `check_access_rights()` usage in tests, and re-validated with `/open_sign` suite passing (`0 failed, 0 errors`). |
| `2026-02-28` | Codex | Closed out `T14` hardening (status bypass guard, template-version immutability, request binding freeze) and completed `T15` with `open.sign.request.signer`, signer sequencing helpers, participant-required send gating, ACL/view wiring, and `/open_sign` tests passing (`0 failed, 0 errors`). |
| `2026-02-28` | Codex | Hardened `T15` after review by blocking non-superuser signer lifecycle/evidence mutations (`state`, `signed_at`, consent/IP/opened fields), requiring at least one actionable signer (`pending/opened`) before send, setting signer lifecycle columns readonly in request UI, and extending tests; `/open_sign` remains green (`0 failed, 0 errors`). |
| `2026-02-28` | Codex | Added explicit ownership of signer evidence-field format validation to `T18` and introduced recurring hardening re-audit task `T610` (with traceability linkage) to catch similar authority/precondition/denial-path gaps in later phases. |
| `2026-02-28` | Codex | Completed `T16` with `open.sign.request.value` model, cross-model integrity constraints, value normalization baselines (text/json by field type), server-authoritative `is_valid` guard, ACL matrix wiring, and dedicated runtime tests; `/open_sign` remains green (`0 failed, 0 errors`). |
| `2026-02-28` | Codex | Closed post-review hardening gap for `T15`/`T16` by applying create-time effective-default checks (blocking `default_*` context bypass for lifecycle/validation fields), enforcing normalization on context-provided defaults, and adding dedicated regression tests; `/open_sign` remains green (`0 failed, 0 errors`). |
| `2026-02-28` | Codex | Completed `T17` with `open.sign.audit.log` (event taxonomy selection, request-local sequence/hash uniqueness, hash-format checks, signer/request consistency, append-only immutability with privileged repair context), added read-only ACL coverage for user/manager/auditor, and added dedicated audit-log tests; `/open_sign` remains green (`0 failed, 0 errors`). |
| `2026-02-28` | Codex | Strengthened process controls by making comprehensive post-change review a mandatory completion/PR gate in `FEATURE.md` and `CONTINUE.md` so every code-change session includes an explicit whole-scope regression and security review step. |
| `2026-02-28` | Codex | Completed `T18` by adding centralized field validation service (`required`/`optional`, type-specific normalization and rule checks), wiring it into `open.sign.request.value` create/write flows, adding signer evidence format validation (`ip_last`, `consent_text_hash`, `signer_timezone`) in `open.sign.request.signer`, and extending regression coverage; `/open_sign` remains green (`0 failed, 0 errors`). |
| `2026-02-28` | Codex | Completed `T19` by adding base backend list/form/kanban coverage and actions for templates, requests, roles, fields, template versions, signers, values, and audit logs; expanded Open Sign menu structure (including configuration and audit visibility), added request form tabs for values/audit logs, and added backend-view regression tests; `/open_sign` remains green (`0 failed, 0 errors`). |
| `2026-02-28` | Codex | Closed T18/T19 post-review security gap by blocking non-superuser signer/value create/write/unlink mutations once requests reach terminal states (`completed`, `cancelled`, `voided`) and adding dedicated denial-path regression tests; `/open_sign` remains green (`0 failed, 0 errors`). |
| `2026-02-28` | Codex | Completed follow-up hardening re-audit fixes: enforced request immutability for terminal states including `cancelled`, preserved retention evidence via request soft-delete behavior validation (no cascade loss of signer/value/audit rows), made multi-record request-value writes savepointed/all-or-nothing, and expanded terminal/atomicity regression coverage; `open_sign` suite remains green (`0 failed, 0 errors`). |
| `2026-02-28` | Codex | Completed `T113` by implementing `open_sign_security.xml` record-rule matrix (company isolation on all operational models plus owner/assignee scope for request-linked models), adding dedicated multi-company/ownership security tests (`test_sign_security_rules.py`), aligning existing ACL fixtures with owner-scoped behavior, and re-validating `/open_sign` (`0 failed, 0 errors` of 69 tests). |
| `2026-02-28` | Codex | Added deferred portal task track `T310`-`T315` for email-only signer authentication via email+token magic links (strategy decision, issuance/revocation, lifecycle hardening, audit taxonomy, and denial-path/E2E tests), and updated traceability/milestone/risk mappings. |
| `2026-03-01` | Codex | Completed `T110` with schema-hardening controls across core models (new SQL checks, FK `ondelete` alignment, and index additions), added create/write pre-validation to preserve deterministic `ValidationError` behavior before DB checks, and revalidated full `/open_sign` (`0 failed, 0 errors`). |
| `2026-03-01` | Codex | Completed `T111` by adding scheduler automation (`data/ir_cron.xml`) and request cron methods for reminder dispatch + expiration transitions, including dedicated cron tests (`test_sign_cron.py`); reminder emails remain intentionally deferred to `T35` while current cron records reminder events via chatter + counters. |
| `2026-03-01` | Codex | Completed `T112` by adding upgrade scripts (`upgrades/1.1/pre-migrate.py`, `upgrades/1.1/post-migrate.py`) and bumping addon version to `1.1`, with conservative data normalization to satisfy new schema constraints during upgrades and full `/open_sign` regression pass (`0 failed, 0 errors`). |
| `2026-03-01` | Codex | Completed recurring hardening re-audit (`T610` / continuation task `T118`) over all completed M1 backend deliverables using the mandatory closeout checklist; no new blocking gaps found, deferred queue remains `DQ-001` (`T35`) and `DQ-002` (`T43`), and full `/open_sign` regression remains green (`0 failed, 0 errors`). |
| `2026-03-01` | Codex | Completed `T23` by adding template-aware signer-role assignment in `open_sign_web` editor (template selector, role selector in field properties, role normalization against template roles, and backend payload role mapping via `role_id`), with regression verification on `/open_sign` (`74 tests, 0 failed`) and module/runtime validation for `/open_sign_web` (known frontend test discovery remains deferred to `T26`). |
| `2026-03-01` | Codex | Applied `T23` hardening follow-up from holistic review: removed silent role reassignment on template switch, removed misleading `Unassigned` assignment path, gated field creation on template-role availability, guarded against stale async role-load responses, and expanded JS utility coverage for role-validity semantics. |
| `2026-03-01` | Codex | Completed `T26` by adding explicit `open_sign_web` frontend runner wiring (`tests/test_js.py` with HOOT `browser_js` + asset registration assertion), tagging module HOOT tests for scoped execution (`open_sign_web`), expanding geometry/validation edge-case coverage, fixing an OWL XML parse blocker (`&amp;&amp;`), and revalidating with `/open_sign_web` (non-zero post-tests) plus `/open_sign` regression (`74 tests, 0 failed`). |
| `2026-03-05` | Codex | Completed `T30` by scaffolding `open_sign_portal` addon structure (`controllers/models/security/views/tests`), adding secure portal route shells (`/my/sign` + signer endpoints) with deny-by-default token posture until `T31`, adding portal page templates, and adding scaffold HTTP/transaction tests; validated with `-i/-u open_sign_portal`, `/open_sign_portal` tests (`0 failed`), and `/open_sign` regression (`0 failed`). |
| `2026-03-05` | Codex | Completed `T31` by extending `open.sign.request.signer` with `portal.mixin` token flow (`access_url` + `get_portal_url()`), adding signer portal link helpers/fields with restricted visibility for non-signing roles, switching portal controller access checks to standard `_document_check_access`, and expanding portal tests for valid-token public access + endpoint envelope consistency; validated with `/open_sign_portal` and `/open_sign` regressions (`0 failed`). |
| `2026-03-05` | Codex | Applied post-`T31` hardening by making signer `access_token` server-authoritative (non-superusers cannot set/mutate portal token fields), adding regression coverage for user/manager token-write denial, and clarifying Phase 3 scope so `T32` must lock signer-action auth policy and `T35` must centralize resend/invitation/reminder/completion links on portal token URLs. |
| `2026-03-09` | Codex | Completed `T32` via remediation subtasks `T32a`-`T32d`: split internal preview from real signer sessions, enforced signer-facing state gates and signer-only mutation auth, made save/submit atomic with rollback-safe locking/revision checks, bound portal rendering/validation to immutable template-version snapshots with legacy fallback/fail-closed handling, blocked active-request field role/delete drift, prevented unsupported portal fields from clearing stored values, and revalidated with `/open_sign_portal`, `/open_sign`, and `scripts/review_gate_open_sign.sh --skip-web` (all green). |
| `2026-03-09` | Codex | Reopened and reclosed `T32d` to align terminal read-only review behavior: real signer and tokenized document routes now support read-only review for `completed`, `declined`, and `expired` requests without mutating evidence; internal preview explicitly allows historical review for `versioned` plus active and reviewable terminal states; `cancelled` and `voided` remain denied; action routes keep returning deterministic `validation_error` responses for authorized-but-immutable requests. |
| `2026-03-09` | Codex | Closed the final `T32` proof gaps with test-only hardening: added explicit regression coverage proving terminal historical preview remains non-mutating and scaffold action endpoints (`decline`, `otp/request`, `otp/verify`) reject terminal requests without mutating signer state, request revision, or audit evidence. `T32` and sub-tasks `T32a`-`T32d` are now closed. |
| `2026-03-10` | Codex | Completed `T33` by hardening ordered-signing portal behavior and the underlying signer contract: sequential out-of-turn signers now receive a read-only waiting session with refresh-to-unlock UX, `save` and `submit` now both return `signing_order_blocked` when out of turn, waiting-page visits do not create `signer_opened` evidence, same-sequence waves remain actionable together, and parallel requests explicitly allow open/save/submit for all mutable signers. To make portal ordering audit-stable, signer contract fields (`request_id`, `partner_id`, `email`, `role_id`, `sequence`) are now frozen for non-superusers once a request reaches `versioned`, and save/submit now re-check mutable-state and ordering under request lock so `stale_revision` takes precedence over order blocking. Validated with `/open_sign`, `/open_sign_portal`, and `scripts/review_gate_open_sign.sh --skip-web` (all green). |
| `2026-03-10` | Codex | Clarified the Phase 3 boundary after `T33`: post-versioning signer contact correction and truthful resend delivery semantics are intentionally deferred to `T35`. Current resend/copy-link behavior is not treated as legal proof of email delivery; `T35` must introduce the controlled manager-only pending-signer email correction path with required reason, token rotation/old-link invalidation, audit evidence, and actual invitation/reminder/completion delivery semantics. |
| `2026-03-10` | Codex | Completed `T34` by replacing the scaffolded signer decline endpoint with a locked `jsonrpc` decline flow: authorized signers can now decline with a required normalized reason from normal or ordered-waiting portal sessions, the declining signer transitions to `declined`, the request transitions immediately to `declined`, other signer records keep their actual prior states, and one `signer_declined` audit event is appended with pre-transition metadata. Waiting-page decline remains intentionally exempt from the `T33` order gate and still does not create `signer_opened` evidence. The portal now exposes a decline modal, post-decline success flash, and readonly decline-reason display for the declining signer, and the implementation was revalidated with `/open_sign`, `/open_sign_portal`, and `scripts/review_gate_open_sign.sh --skip-web` (all green). |
| `2026-03-10` | Codex | Completed `T35` by introducing real queued notification delivery and canonical portal-link usage across `open_sign` and `open_sign_portal`: initial send now queues invitation mail for the current actionable signer wave and rolls back the send transition on queue failure; reminders now target actionable signers only and update counters only when at least one reminder is queued; completion now appends `request_completed` and best-effort queues owner + signer notifications with the final attachment; portal submit now best-effort queues next-wave invitations; portal decline now best-effort queues an owner-only decline notification. Canonical signer share/copy/invitation/reminder/completion links now use `get_portal_url()` / `portal_sign_url`, notification audit events (`notification_queued` / `notification_failed` / `notification_skipped`) and `signer_contact_corrected` were added, and the old fake resend action was replaced with a manager-only pending-signer contact-correction/resend wizard that requires a reason, rotates the signer token on every resend, defers delivery for `versioned` or future-wave signers, and rolls back atomic actionable resends on queue failure. Validated with `/open_sign` (`119 tests, 0 failed`), `/open_sign_portal` (`97 tests, 0 failed`), and `scripts/review_gate_open_sign.sh --skip-web` (passed). |
| `2026-03-11` | Codex | Applied the `T35` closeout fix after full review: base `open.sign.request.signer._get_notification_sign_url()` no longer falls back to the internal backend `sign_access_url`, so signer-facing invitation/reminder/completion links are available only when `open_sign_portal` supplies a real tokenized portal URL. This makes invitation/send and actionable manual resend fail truthfully instead of emailing backend links, while reminder and signer-completion flows now skip truthfully when a signer portal URL is unavailable and owner-only completion/decline mail remains valid. Strengthened proof coverage by asserting completion mail link + attachment semantics, adding rollback coverage for missing signer notification URLs, and adding backend view-arch checks for manager-only resend visibility plus canonical copy-link exposure. Revalidated with `/open_sign` (`122 tests, 0 failed`) and `/open_sign_portal` (`99 tests, 0 failed`). |
| `2026-03-11` | Codex | Applied the final `T35` closeout hardening after full closeout review: atomic invitation failures now persist durable `notification_failed` audit evidence outside the rolled-back savepoint for both `action_send()` and actionable manager resend/correction, covering missing signer portal URLs, missing invitation templates, and queue exceptions without weakening the atomic rollback of request/resend state. Best-effort reminder/completion/decline flows remain unchanged. Revalidated with `/open_sign`, `/open_sign_portal`, and `scripts/review_gate_open_sign.sh --skip-web` (all green). |
| `2026-03-11` | Codex | Completed the final `T35` closeout sanitization pass: `notification_failed.metadata_json.failure_reason` now stores only stable safe codes (`missing_template`, `signer_notification_url_unavailable`, `mail_queue_error`, `notification_service_error`) across invitation, reminder, completion, decline, and wrapper failure paths; raw notification exceptions now go only to server logs; atomic invitation failures still persist durable failure audit while user-facing queue errors remain deterministic and token-safe. Revalidated with `/open_sign` (`123 tests, 0 failed`), `/open_sign_portal` (`100 tests, 0 failed`), and `scripts/review_gate_open_sign.sh --skip-web` (passed). |
| `2026-03-12` | Codex | Completed `T36` by adding a dedicated portal security suite (`test_portal_security.py`) plus shared portal test helpers (`open_sign_portal/tests/common.py`) to cover the current signer-token lifecycle, replay/stale/lock denial paths, rotated-token invalidation across page/document/JSONRPC routes, waiting-signer abuse boundaries, terminal replay immutability, and no-leak assertions for denial/audit paths. The implementation did not add token expiry, throttling, idempotency storage, or new portal models; those remain deferred to `T37`, `T316`/`T317`, and later artifact/token tasks. Revalidated with `/open_sign` (`107 tests, 0 failed`), `/open_sign_portal` (`132 tests, 0 failed` / `open_sign_portal: 140 tests`), and `scripts/review_gate_open_sign.sh --skip-web` (passed). |
| `2026-03-13` | Codex | Completed `T37` by implementing optional per-signer email OTP verification in `open_sign_portal` as a submit-time gate: signer records now carry frozen `otp_required` policy plus server-managed `otp_verified_at`, OTP challenges are stored as salted PBKDF2 hashes in the new `open.sign.otp.challenge` model, and portal `otp/request` + `otp/verify` JSONRPC flows now enforce ordered-signing actionability, `60s` resend cooldown, `10m` TTL, `5` invalid-attempt limit, and deterministic validation messages without storing raw OTP values. OTP mail is queued atomically through the T35 notification service with durable sanitized `notification_failed` audit on template/queue failure, invitation/reminder templates now mention OTP when required, submit is blocked until OTP verification is complete, decline remains OTP-exempt, and manual resend/contact correction revokes active OTP challenge state. Revalidated with `/open_sign` (`127 tests, 0 failed`), `/open_sign_portal` (`176 tests, 0 failed`), and `scripts/review_gate_open_sign.sh --skip-web` (passed). |
| `2026-03-13` | Codex | Completed `T38` by locking the shipped Phase 3 portal JSONRPC contract to a single controller response layer plus explicit contract tests. `doc/open_sign/m0/PORTAL_API_CONTRACT.md` now matches the runtime behavior, including redirect-style success envelopes for `decline`, `otp/request`, and `otp/verify`; active runtime error codes are now explicitly separated from reserved/deferred codes; and the new `test_portal_contract.py` suite locks exact success/error envelope shape, route-specific allowed error-code behavior, reserved-code non-emission, and no-token-leak guarantees for mutating portal routes. Revalidated with `/open_sign_portal`, `/open_sign`, and `scripts/review_gate_open_sign.sh --skip-web` (all green). |
