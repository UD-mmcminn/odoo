# Open Sign Agent Workflow Guardrails

These rules are mandatory for any coding session in this repository.

## Session Start

1. Read [CONTINUE.md](/workspaces/odoo/CONTINUE.md) first.
2. Read [FEATURE.md](/workspaces/odoo/FEATURE.md) and identify the active task ID(s).
3. State the active task ID(s) before implementing changes.

## Implementation Flow

1. Implement one coherent task slice at a time.
2. Keep server-side rules authoritative; UI checks are convenience only.
3. Add or update tests in the same slice for new behavior and denial paths.
4. If scope is deferred, log task ID, risk, and follow-up owner in `FEATURE.md` and `CONTINUE.md`.

## Mandatory Closeout Gate (Before Task Completion)

1. Run `scripts/review_gate_open_sign.sh` for the task scope.
2. Execute [REVIEW_CHECKLIST.md](/workspaces/odoo/REVIEW_CHECKLIST.md) line-by-line.
3. Confirm no unresolved high-severity security, authority-boundary, or regression issues.
4. Update `FEATURE.md` task status and `CONTINUE.md` session context.

Do not mark a task complete unless all closeout gate items are satisfied.
