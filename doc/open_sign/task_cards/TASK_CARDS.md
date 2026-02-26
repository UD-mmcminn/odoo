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
Goal: Add portal addon ACL/rules (`security/ir.model.access.csv`, portal model record rules) for session/OTP models.
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
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
Rollback/Migration Impact: Document schema/data migration effects if model or XML data changes.

## T115

Task ID: T115
Goal: Add duplicate-submit and race-condition test coverage for portal signer flows.
Phase: Phase 3
Requirements: `R-021`, `R-024`
Dependencies: Phase 1 ready; portal token model available
Target Files: addons/open_sign_portal/controllers/*, addons/open_sign_portal/models/*, addons/open_sign_portal/security/*, addons/open_sign_portal/tests/*
Implementation Notes: Follow schema/API/security contracts defined in FEATURE.md and M0 deliverables.
Acceptance Criteria: Behavior matches task goal, related tests pass, traceability references updated.
Test Plan: Add/extend unit/integration/http/js tests as required by task scope.
Security Notes: Verify ACL, token scope, and audit implications when applicable.
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
