# Open Sign Post-Change Review Checklist

Use this checklist before marking any task complete.

## 1. Task Contract

- [ ] The diff matches the active task scope in `FEATURE.md`.
- [ ] Requirement IDs and acceptance criteria are still satisfied.
- [ ] Any scope drift is documented as a change note.

## 2. Authority Boundaries

- [ ] Server-authoritative fields cannot be directly overridden by client/user input.
- [ ] State transitions enforce preconditions server-side.
- [ ] UI readonly/visibility behavior matches server write authority.

## 3. Security and Data Exposure

- [ ] ACLs and record rules still enforce least privilege.
- [ ] No new data leakage paths were introduced (portal/public/internal boundaries).
- [ ] Tokenized/public endpoints were reviewed for replay and abuse behavior.

## 4. Data Integrity and Lifecycle

- [ ] Model constraints (SQL/Python) protect core invariants.
- [ ] Soft-delete/archive policies are preserved where required.
- [ ] Evidence/audit retention behavior is unchanged unless explicitly scoped.

## 5. Odoo Conventions and API Health

- [ ] No deprecated API usage introduced.
- [ ] Override signatures and ORM patterns remain Odoo-compliant.
- [ ] Views/security/data file loading order remains valid.

## 6. Tests and Verification

- [ ] Targeted backend tests were executed and passed.
- [ ] Targeted frontend tests were executed and passed (or explicitly deferred with task/risk).
- [ ] Regression checks covered adjacent flows touched by the change.

## 7. Deferred Items Tracking

- [ ] Each deferment has task ID, risk summary, and planned follow-up task.
- [ ] Deferments are captured in both `FEATURE.md` and `CONTINUE.md` when applicable.

## 8. Final Documentation Update

- [ ] `FEATURE.md` reflects task status, traceability, and notable decisions.
- [ ] `CONTINUE.md` captures what changed, why it matters, and what is next.
- [ ] Reviewer notes include known residual risk (if any).
