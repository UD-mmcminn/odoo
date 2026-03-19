# Open Sign Task Cards

Status: Finalized for M0 (`T91`)
Date: 2026-02-26

This file contains template-based task cards for all currently open tasks outside the M0 documentation bundle (`T90`-`T99`).

Card format follows the task-card template from `FEATURE.md`.

## T01

Task ID: T01
Goal: Confirm Odoo target version and compatibility constraints.
Phase: Phase 0
Requirements: (none linked yet)
Dependencies: Design control baseline
Target Files: FEATURE.md, doc/open_sign/m0/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T02

Task ID: T02
Goal: Finalize addon names, dependencies, and install order.
Phase: Phase 0
Requirements: (none linked yet)
Dependencies: Design control baseline
Target Files: FEATURE.md, doc/open_sign/m0/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T03

Task ID: T03
Goal: Define legal/compliance acceptance criteria (audit, retention, consent).
Phase: Phase 0
Requirements: `R-022`
Dependencies: Design control baseline
Target Files: FEATURE.md, doc/open_sign/m0/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T04

Task ID: T04
Goal: Approve wireframes for template editor and signer portal.
Phase: Phase 0
Requirements: (none linked yet)
Dependencies: Design control baseline
Target Files: FEATURE.md, doc/open_sign/m0/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T05

Task ID: T05
Goal: Decide PDF processing stack and licensing constraints.
Phase: Phase 0
Requirements: `R-019`
Dependencies: Design control baseline
Target Files: FEATURE.md, doc/open_sign/m0/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T06

Task ID: T06
Goal: Finalize status transition matrix, ACL matrix, and cross-model invariants from the schema contract.
Phase: Phase 0
Requirements: `R-011`, `R-012`, `R-019`
Dependencies: Design control baseline
Target Files: FEATURE.md, doc/open_sign/m0/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T07

Task ID: T07
Goal: Define evidence retention, archival, and purge policy.
Phase: Phase 0
Requirements: `R-013`
Dependencies: Design control baseline
Target Files: FEATURE.md, doc/open_sign/m0/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T08

Task ID: T08
Goal: Define observability baseline (events, metrics, alerts).
Phase: Phase 0
Requirements: `R-015`, `R-025`
Dependencies: Design control baseline
Target Files: FEATURE.md, doc/open_sign/m0/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T09

Task ID: T09
Goal: Finalize Odoo compliance checklist (lint, module structure, route/model conventions, XML `noupdate`/external-ID policy).
Phase: Phase 0
Requirements: `R-017`
Dependencies: Design control baseline
Target Files: FEATURE.md, doc/open_sign/m0/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T10

Task ID: T10
Goal: Scaffold addon with manifest/init/security skeleton.
Phase: Phase 1
Requirements: (none linked yet)
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T11

Task ID: T11
Goal: Implement `open.sign.template` model + views.
Phase: Phase 1
Requirements: `R-001`
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T12

Task ID: T12
Goal: Implement `open.sign.role` model + assignment flows.
Phase: Phase 1
Requirements: `R-004`
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T13

Task ID: T13
Goal: Implement `open.sign.template.field` + `open.sign.template.field.option`.
Phase: Phase 1
Requirements: `R-002`
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T14

Task ID: T14
Goal: Implement `open.sign.request` model + status engine.
Phase: Phase 1
Requirements: `R-006`, `R-012`
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T15

Task ID: T15
Goal: Implement `open.sign.request.signer` with sequence logic.
Phase: Phase 1
Requirements: `R-004`
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T16

Task ID: T16
Goal: Implement `open.sign.request.value` storage and normalization.
Phase: Phase 1
Requirements: (none linked yet)
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T17

Task ID: T17
Goal: Implement `open.sign.audit.log` immutable records.
Phase: Phase 1
Requirements: `R-007`
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T18

Task ID: T18
Goal: Implement validation service for required/optional and field-type checks.
Phase: Phase 1
Requirements: `R-003`, `R-026`
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T19

Task ID: T19
Goal: Create base backend menus and form/tree/kanban views.
Phase: Phase 1
Requirements: (none linked yet)
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T110

Task ID: T110
Goal: Add SQL constraints, FK `ondelete` policies, and indexes per schema contract.
Phase: Phase 1
Requirements: (none linked yet)
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T111

Task ID: T111
Goal: Implement cron jobs for reminders and expiration.
Phase: Phase 1
Requirements: (none linked yet)
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T112

Task ID: T112
Goal: Add core migration hooks and upgrade scripts aligned to schema contract evolution.
Phase: Phase 1
Requirements: `R-014`
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T113

Task ID: T113
Goal: Implement security groups + ACL/record-rule matrix from design baseline.
Phase: Phase 1
Requirements: `R-011`, `R-020`
Dependencies: T10 scaffold first, then model/security dependencies by task order
Target Files: addons/open_sign/models/*, addons/open_sign/security/*, addons/open_sign/views/*, addons/open_sign/services/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T20

Task ID: T20
Goal: Scaffold addon and declare backend/frontend assets in `__manifest__.py`.
Phase: Phase 2
Requirements: `R-017`
Dependencies: Phase 1 model APIs stabilized
Target Files: addons/open_sign_web/static/src/*, addons/open_sign_web/static/tests/*, addons/open_sign_web/__manifest__.py
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T21

Task ID: T21
Goal: Build template canvas with drag/drop/resizing on PDF pages.
Phase: Phase 2
Requirements: `R-001`
Dependencies: Phase 1 model APIs stabilized
Target Files: addons/open_sign_web/static/src/*, addons/open_sign_web/static/tests/*, addons/open_sign_web/__manifest__.py
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T22

Task ID: T22
Goal: Build field palette and field property editor.
Phase: Phase 2
Requirements: (none linked yet)
Dependencies: Phase 1 model APIs stabilized
Target Files: addons/open_sign_web/static/src/*, addons/open_sign_web/static/tests/*, addons/open_sign_web/__manifest__.py
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T23

Task ID: T23
Goal: Implement signer role assignment in editor.
Phase: Phase 2
Requirements: (none linked yet)
Dependencies: Phase 1 model APIs stabilized
Target Files: addons/open_sign_web/static/src/*, addons/open_sign_web/static/tests/*, addons/open_sign_web/__manifest__.py
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T24

Task ID: T24
Goal: Implement client-side value validation aligned with server rules.
Phase: Phase 2
Requirements: `R-002`, `R-003`, `R-026`
Dependencies: Phase 1 model APIs stabilized
Target Files: addons/open_sign_web/static/src/*, addons/open_sign_web/static/tests/*, addons/open_sign_web/__manifest__.py
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T25

Task ID: T25
Goal: Implement signature adoption dialog (draw/type/upload).
Phase: Phase 2
Requirements: `R-005`
Dependencies: Phase 1 model APIs stabilized
Target Files: addons/open_sign_web/static/src/*, addons/open_sign_web/static/tests/*, addons/open_sign_web/__manifest__.py
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T26

Task ID: T26
Goal: Add JS tests for geometry and validation payloads.
Phase: Phase 2
Requirements: (none linked yet)
Dependencies: Phase 1 model APIs stabilized
Target Files: addons/open_sign_web/static/src/*, addons/open_sign_web/static/tests/*, addons/open_sign_web/__manifest__.py
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T30

Task ID: T30
Goal: Scaffold addon with controller/routes and portal templates.
Phase: Phase 3
Requirements: (none linked yet)
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T31

Task ID: T31
Goal: Extend signer model with `portal.mixin` and standard access-token URL flow.
Phase: Phase 3
Requirements: `R-009`
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T32

Task ID: T32
Goal: Implement signing session open/save/submit flows.
Phase: Phase 3
Requirements: `R-005`, `R-009`
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T33

Task ID: T33
Goal: Enforce signer order (sequential and parallel policies).
Phase: Phase 3
Requirements: `R-004`
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T34

Task ID: T34
Goal: Implement decline flow and reason capture.
Phase: Phase 3
Requirements: (none linked yet)
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T35

Task ID: T35
Goal: Add reminder/invitation/completion notifications.
Phase: Phase 3
Requirements: (none linked yet)
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T36

Task ID: T36
Goal: Add portal security tests for replay and token abuse.
Phase: Phase 3
Requirements: `R-009`, `R-016`, `R-021`, `R-023`, `R-024`
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T37

Task ID: T37
Goal: Implement optional OTP verification flow.
Phase: Phase 3
Requirements: `R-016`
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T38

Task ID: T38
Goal: Implement endpoint response envelope/error codes and contract tests.
Phase: Phase 3
Requirements: `R-021`, `R-024`
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T39

Task ID: T39
Goal: Add portal addon ACL/rules (`security/ir.model.access.csv`, portal model record rules) for the current portal-persisted model surface, primarily `open.sign.otp.challenge` as a system-only ORM model, and lock related portal signer field exposure.
Phase: Phase 3
Requirements: `R-020`
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T114

Task ID: T114
Goal: Implement idempotency-key handling and concurrency-safe locking for submit/decline.
Phase: Phase 3
Requirements: `R-021`, `R-024`
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Completed in `T316` with durable system-only `open.sign.portal.idempotency` storage for `submit` / `decline`, committed-success replay, same-key different-payload conflict detection, and frontend idempotency-key reuse for unresolved retries.
Acceptance Criteria: Completed; behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Completed with new transaction/http coverage in `test_portal_idempotency.py` plus contract updates in `test_portal_contract.py`.
Security Notes: System-only ORM access and company-scoped rule are required because `response_json` stores replay payloads with tokenized redirect URLs.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T115

Task ID: T115
Goal: Add duplicate-submit and race-condition test coverage for portal signer flows.
Phase: Phase 3
Requirements: `R-021`, `R-024`
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Completed in `T317` with a dedicated `test_portal_race.py` suite plus shared overlap helpers in `open_sign_portal/tests/common.py`. Because `HttpCase` runs under `TestCursor`, which serializes concurrent requests, the shipped coverage uses deterministic controller-level overlap orchestration with isolated DB cursors and mocked portal request contexts plus a minimal true-concurrency smoke layer at the controller/DB-lock level, with no public contract changes.
Acceptance Criteria: Completed; same-key overlap, same-key different-payload overlap, different-key overlap, submit-vs-decline overlap, and ordered-signing cross-signer overlap are all covered with side-effect singularity assertions and related tests pass.
Test Plan: Completed with new race coverage in `test_portal_race.py`, reused HTTP/controller helpers in `common.py`, full `/open_sign_portal` and `/open_sign` validation, and two additional fresh-database race-file runs to check for flake. Literal overlapping public HTTP dispatcher proof was not achievable under the current `HttpCase`/`TestCursor` model and is deferred separately to `T317a` if still desired.
Security Notes: Coverage confirms request-row locking plus durable idempotency prevent contradictory terminal evidence, duplicate submit/decline side effects, and same-key replay drift under overlap.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T317a

Task ID: T317a
Goal: Add deferred live-HTTP overlap verification for portal signer flows using an out-of-band harness that bypasses `HttpCase`/`TestCursor` request serialization.
Phase: Phase 3
Requirements: `R-021`, `R-024`
Dependencies: `T316`, `T317` complete; portal token model available
Target Files: addons/open_sign_portal/tests/*, supporting local test harness files if needed
Implementation Notes: Deferred and non-blocking for `T310`. Build a verification-only harness outside the standard `HttpCase` request path so real overlapping public portal HTTP requests can be exercised end-to-end with isolated clients and without `TestCursor` request serialization.
Acceptance Criteria: Real overlapping public HTTP submit/decline requests are proven to preserve the same lock/idempotency/side-effect guarantees already covered by controller-level T317 tests, without changing the public contract.
Test Plan: Use a separate process/server or other non-`TestCursor` harness to hit the real public portal routes with isolated HTTP clients and confirm the T317 controller/DB-lock outcomes hold through the full dispatcher stack.
Security Notes: Verification-only follow-up; intended to widen confidence in overlap behavior, not to change current portal security semantics.
Rollback/Migration Impact: None expected unless the deferred harness introduces dedicated support files.

## T310

Task ID: T310
Goal: Define and document the external email-signer token strategy before the `T311`-`T315` implementation slice.
Phase: Phase 3
Requirements: `R-009`
Dependencies: `T31`, `T35`, `T38` complete; portal token model available
Target Files: FEATURE.md, CONTINUE.md, doc/open_sign/task_cards/TASK_CARDS.md, doc/open_sign/m0/PORTAL_API_CONTRACT.md
Implementation Notes: Completed as a doc-only strategy lock. External email-only signer links reuse `open.sign.request.signer.access_token` from `portal.mixin`, keep the existing signer route family as the only public entry path, resolve external signer context from `signer_id + access_token` without any email-based ACL lookup, remain multi-use until rotated/revoked/expired, and defer `expired_token` activation to `T313`. The locked expiry policy is `min(72 hours from issuance, request expiry)`; manual resend/contact correction rotate the token; ordinary reminders reuse a still-valid active token; and token lifecycle metadata stays on `open.sign.request.signer` rather than in a separate token model.
Acceptance Criteria: Completed; `D-011` is resolved, `T311`-`T315` inherit the locked token policy, and no runtime code changes are introduced.
Test Plan: Completed with documentation consistency review (`FEATURE.md`, `CONTINUE.md`, task cards, and portal contract docs) plus `git diff --check`; no Odoo runtime test run required because the task is documentation-only.
Security Notes: Baseline possession-of-link risk for email-only signers is explicitly accepted and recorded; compensating controls remain deferred to `T311`-`T314`.
Rollback/Migration Impact: None; strategy/documentation only.

## T311

Task ID: T311
Goal: Implement email-invitation magic-link issuance for email-only signers with resend rotation and explicit token revocation hooks.
Phase: Phase 3
Requirements: `R-009`
Dependencies: `T310` complete; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/tests/*, related mail/notification files
Implementation Notes: Completed. `open.sign.request.signer` now stores `email_token_issued_at`, `email_token_expires_at`, and `email_token_revoked_at`; invitation delivery uses explicit signer-token lifecycle helpers; initial send, wave-unblocked invitation, and manual resend/contact correction always rotate to a fresh distributed signer token; reminders reuse an active token and refresh missing/revoked/metadata-expired tokens; backend copy-link surfaces now expose only currently distributable signer URLs and never mint tokens on read; signer completion notifications now skip when no currently distributable signer URL exists; and explicit revoke is a manager-only pending-signer action that rotates the hidden token, stamps revocation metadata, invalidates active OTP challenge state, and does not send a replacement link. The implementation keeps signer `portal.mixin` `access_token` as the only magic-link secret, adds no new public routes, and leaves dedicated `token_*` audit event types deferred to `T314`.
Acceptance Criteria: Completed; lifecycle metadata, delivery-time issue/reuse semantics, blank-until-issued backend copy-link behavior, completion-link suppression when no distributable signer URL exists, explicit revoke, revoked-link invalidation, reminder refresh behavior, migration backfill, and related tests are in place.
Test Plan: Completed via new portal email-token transaction/http coverage, upgrade backfill coverage, resend/reminder/revoke regression coverage, and full `open_sign` / `open_sign_portal` validation.
Security Notes: External email-only signers remain token-only; matching an internal user by email does not grant access; revoked/rotated links fail with the existing `invalid_token` behavior; and runtime expiry enforcement is now implemented in `T313`.
Rollback/Migration Impact: Adds signer lifecycle fields and a `1.1` portal upgrade backfill for existing signers that already have `access_token` but no lifecycle metadata.

## T312

Task ID: T312
Goal: Implement public token entry and signer-context resolution for email-only signers without email-based ACL authorization.
Phase: Phase 3
Requirements: `R-009`
Dependencies: `T310`, `T311` complete; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/tests/*
Implementation Notes: Completed. `open_sign_portal` controller access resolution now separates external signer token access from internal partner-linked fallback explicitly. External email-only signer access resolves strictly from `signer_id + access_token`; matching an internal user by email does not grant access; exact linked internal fallback remains limited to `partner_id`; and a wrong/stale token does not suppress that exact linked internal fallback. Public GET denial remains redirect-to-`/my`, JSONRPC denial remains `invalid_token`, and no new routes or error codes were introduced. To preserve the separate internal preview surface while tightening generic no-token document access, preview pages now use an internal-only `preview=1` PDF link rather than relying on the generic document fallback path.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Completed with extended portal HTTP coverage for same-email spoof denial on page/document/JSON/OTP routes, authenticated valid-token success for unrelated internal users, exact `partner_id` fallback with wrong/stale token, and preview-document regression coverage.
Security Notes: Token identity remains constant-time and server-authoritative; email similarity or mailbox overlap does not widen access; the internal preview surface remains separate from external signer token entry.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T313

Task ID: T313
Goal: Implement token lifecycle hardening for email-only signers (expiry, revoke, replay handling, invalid-attempt throttling, and deterministic error codes).
Phase: Phase 3
Requirements: `R-009`, `R-021`
Dependencies: `T310`-`T312` complete; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/tests/*, contract docs if runtime codes change
Implementation Notes: Completed. Current signer-token access is now enforced from lifecycle metadata on `open.sign.request.signer` rather than from raw token equality alone. `open_sign_portal` now classifies exact current-token matches as `valid`, `expired`, `revoked`, or `invalid`; signer JSONRPC routes emit `expired_token` only for genuinely expired current links; public GET denial remains redirect-to-`/my`; rotated/revoked/tampered/missing/metadata-incomplete links still map to `invalid_token`; and the T313 closeout hardens signer+IP invalid-link throttling with a system-only aggregate bucket model, a system-only attempt-log model, and `token_security_service` providing rolling-window invalid-attempt tracking, concurrency-safe invalid-attempt persistence, and best-effort non-blocking clear on valid token-auth success, with no new public throttle error code. Readonly `/document` now participates in the same record-and-clear throttle lifecycle. Exact linked internal fallback still works with wrong/revoked/expired token input, but internal-fallback sessions no longer echo stale token state back into DOM values, document URLs, refresh URLs, or success redirects.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Completed with a new `test_portal_token_security.py` suite plus extended contract, security, OTP, email-token, and ACL coverage. The shipped tests now lock token classification, signer+IP throttle isolation and cleanup, rolling-window invalid-attempt tracking, concurrency-safe invalid-attempt persistence, best-effort non-blocking clear behavior, readonly `/document` throttle participation, active `expired_token` envelopes on signer JSONRPC routes, redirect-only GET denial for expired links, runtime denial of hidden post-revoke current tokens, no-token-echo behavior for internal fallback, and externally indistinguishable `invalid_token` behavior for throttled invalid attempts.
Security Notes: Expiry and revoke checks now apply before signer mutation; denial paths remain deterministic and token-safe; throttling is best-effort abuse control keyed by signer+IP; and token lifecycle audit chronology remains deferred to `T314`.
Rollback/Migration Impact: No signer business-data migration is required. `open_sign_portal` version `1.3` adds the `open.sign.portal.token.throttle.attempt` table, keeps throttle models system-only, preserves the daily garbage-collection cron for stale throttle state, and wipes pre-closeout `open.sign.portal.token.throttle` rows on upgrade because they were created under the flawed first-attempt-anchored semantics.

## T314

Task ID: T314
Goal: Extend audit/evidence taxonomy for email-token events (`token_issued`, `token_opened`, `token_rejected`, `token_revoked`) with export coverage.
Phase: Phase 3
Requirements: `R-007`
Dependencies: `T310` complete; `T311`-`T313` in place where needed for actual event emission
Target Files: addons/open_sign/models/*, addons/open_sign_portal/controllers/*, addons/open_sign_portal/tests/*, evidence/export docs
Implementation Notes: Use the locked email-token event taxonomy from `T310`. Record lifecycle chronology without storing raw token values or full tokenized URLs in audit metadata.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend audit-log and export tests for issuance/open/reject/revoke event coverage and sanitization behavior.
Security Notes: Audit evidence must describe token lifecycle safely without turning audit storage into a secret store.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T315

Task ID: T315
Goal: Add end-to-end and denial-path tests for email-only signer flow (tampered/expired/revoked token, spoofed email no-access, replay, and controlled link-sharing behavior).
Phase: Phase 3
Requirements: `R-009`, `R-021`
Dependencies: `T310`-`T314` complete enough for end-to-end behavior
Target Files: addons/open_sign_portal/tests/*, related contract/security docs if needed
Implementation Notes: Tests must target the locked `T310` strategy: same signer route family, signer `portal.mixin` token carrier, token-only external signer resolution, `min(72h, request expiry)` expiry policy, and no email-based ACL fallback for external email-only signers.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend end-to-end, denial-path, replay, and abuse tests for tampered/expired/revoked tokens, spoofed email access denial, and controlled link-sharing behavior under the accepted baseline risk model.
Security Notes: The suite must prove the email-only track preserves the same no-leak and deterministic denial standards as the current portal baseline.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T40

Task ID: T40
Goal: Implement value-to-PDF rendering/flattening.
Phase: Phase 4
Requirements: `R-001`, `R-008`, `R-028`
Dependencies: Phases 1 and 3 ready for end-to-end flow
Target Files: addons/open_sign/services/*, addons/open_sign/report/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T41

Task ID: T41
Goal: Generate final signed attachment and lock request edits.
Phase: Phase 4
Requirements: `R-008`, `R-028`
Dependencies: Phases 1 and 3 ready for end-to-end flow
Target Files: addons/open_sign/services/*, addons/open_sign/report/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T42

Task ID: T42
Goal: Build completion certificate/evidence summary page.
Phase: Phase 4
Requirements: `R-027`
Dependencies: Phases 1 and 3 ready for end-to-end flow
Target Files: addons/open_sign/services/*, addons/open_sign/report/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T43

Task ID: T43
Goal: Extend audit logging with hash-chain integrity checks.
Phase: Phase 4
Requirements: `R-006`, `R-007`
Dependencies: Phases 1 and 3 ready for end-to-end flow
Target Files: addons/open_sign/services/*, addons/open_sign/report/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T44

Task ID: T44
Goal: Add end-to-end tests from send -> sign -> complete.
Phase: Phase 4
Requirements: `R-002`, `R-003`, `R-004`, `R-005`, `R-006`, `R-008`, `R-012`, `R-026`
Dependencies: Phases 1 and 3 ready for end-to-end flow
Target Files: addons/open_sign/services/*, addons/open_sign/report/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T45

Task ID: T45
Goal: Add audit package export (values, timeline, metadata).
Phase: Phase 4
Requirements: `R-013`, `R-027`, `R-028`
Dependencies: Phases 1 and 3 ready for end-to-end flow
Target Files: addons/open_sign/services/*, addons/open_sign/report/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T46

Task ID: T46
Goal: Persist consent/legal snapshot and include it in audit package output.
Phase: Phase 4
Requirements: `R-022`
Dependencies: Phases 1 and 3 ready for end-to-end flow
Target Files: addons/open_sign/services/*, addons/open_sign/report/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T47

Task ID: T47
Goal: Apply tokenized access policy for generated signed artifacts and payload attachments.
Phase: Phase 4
Requirements: `R-023`
Dependencies: Phases 1 and 3 ready for end-to-end flow
Target Files: addons/open_sign/services/*, addons/open_sign/report/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T116

Task ID: T116
Goal: Implement UTC timestamp trust policy checks and include clock metadata in evidence export.
Phase: Phase 4
Requirements: `R-025`
Dependencies: Phases 1 and 3 ready for end-to-end flow
Target Files: addons/open_sign/services/*, addons/open_sign/report/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T117

Task ID: T117
Goal: Persist source/final PDF SHA-256 digests and verify during evidence export.
Phase: Phase 4
Requirements: `R-008`, `R-028`
Dependencies: Phases 1 and 3 ready for end-to-end flow
Target Files: addons/open_sign/services/*, addons/open_sign/report/*, addons/open_sign/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T50

Task ID: T50
Goal: Scaffold optional addon and profile models.
Phase: Phase 5
Requirements: `R-010`
Dependencies: Phase 4 artifact flow finalized
Target Files: addons/open_sign_certificate/models/*, addons/open_sign_certificate/services/*, addons/open_sign_certificate/views/*, addons/open_sign_certificate/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T51

Task ID: T51
Goal: Implement PDF certificate signing service.
Phase: Phase 5
Requirements: `R-010`
Dependencies: Phase 4 artifact flow finalized
Target Files: addons/open_sign_certificate/models/*, addons/open_sign_certificate/services/*, addons/open_sign_certificate/views/*, addons/open_sign_certificate/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T52

Task ID: T52
Goal: Implement signature verification and persisted results.
Phase: Phase 5
Requirements: `R-010`
Dependencies: Phase 4 artifact flow finalized
Target Files: addons/open_sign_certificate/models/*, addons/open_sign_certificate/services/*, addons/open_sign_certificate/views/*, addons/open_sign_certificate/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T53

Task ID: T53
Goal: Add admin configuration views and access control.
Phase: Phase 5
Requirements: (none linked yet)
Dependencies: Phase 4 artifact flow finalized
Target Files: addons/open_sign_certificate/models/*, addons/open_sign_certificate/services/*, addons/open_sign_certificate/views/*, addons/open_sign_certificate/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T54

Task ID: T54
Goal: Add optional integration tests.
Phase: Phase 5
Requirements: (none linked yet)
Dependencies: Phase 4 artifact flow finalized
Target Files: addons/open_sign_certificate/models/*, addons/open_sign_certificate/services/*, addons/open_sign_certificate/views/*, addons/open_sign_certificate/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T60

Task ID: T60
Goal: Performance test with large PDFs and multi-signer load.
Phase: Phase 6
Requirements: (none linked yet)
Dependencies: Phases 1-4 complete; optional Phase 5 where applicable
Target Files: addons/open_sign*/tests/*, CI config, operational docs
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T61

Task ID: T61
Goal: Security review (token handling, PII, permission boundaries).
Phase: Phase 6
Requirements: `R-007`, `R-011`, `R-016`, `R-020`, `R-025`
Dependencies: Phases 1-4 complete; optional Phase 5 where applicable
Target Files: addons/open_sign*/tests/*, CI config, operational docs
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T62

Task ID: T62
Goal: Accessibility and mobile signing UX validation.
Phase: Phase 6
Requirements: (none linked yet)
Dependencies: Phases 1-4 complete; optional Phase 5 where applicable
Target Files: addons/open_sign*/tests/*, CI config, operational docs
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T63

Task ID: T63
Goal: Regression suite and CI integration.
Phase: Phase 6
Requirements: `R-014`, `R-027`
Dependencies: Phases 1-4 complete; optional Phase 5 where applicable
Target Files: addons/open_sign*/tests/*, CI config, operational docs
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T64

Task ID: T64
Goal: Prepare deployment/migration and operator runbook.
Phase: Phase 6
Requirements: `R-014`
Dependencies: Phases 1-4 complete; optional Phase 5 where applicable
Target Files: addons/open_sign*/tests/*, CI config, operational docs
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T65

Task ID: T65
Goal: UAT signoff and release checklist completion.
Phase: Phase 6
Requirements: `R-018`
Dependencies: Phases 1-4 complete; optional Phase 5 where applicable
Target Files: addons/open_sign*/tests/*, CI config, operational docs
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T66

Task ID: T66
Goal: Add observability dashboards and failure alerts.
Phase: Phase 6
Requirements: `R-015`
Dependencies: Phases 1-4 complete; optional Phase 5 where applicable
Target Files: addons/open_sign*/tests/*, CI config, operational docs
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T67

Task ID: T67
Goal: Execute backup/restore and failure-recovery validation.
Phase: Phase 6
Requirements: (none linked yet)
Dependencies: Phases 1-4 complete; optional Phase 5 where applicable
Target Files: addons/open_sign*/tests/*, CI config, operational docs
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T68

Task ID: T68
Goal: Run data retention and purge dry-run verification.
Phase: Phase 6
Requirements: `R-013`
Dependencies: Phases 1-4 complete; optional Phase 5 where applicable
Target Files: addons/open_sign*/tests/*, CI config, operational docs
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T69

Task ID: T69
Goal: Run lint/conformance checks (`test_lint` subset, manifest and module structure checks).
Phase: Phase 6
Requirements: `R-017`
Dependencies: Phases 1-4 complete; optional Phase 5 where applicable
Target Files: addons/open_sign*/tests/*, CI config, operational docs
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.
