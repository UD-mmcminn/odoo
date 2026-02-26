# Open Sign Developer Command Cookbook

Status: Finalized for M0 (`T93`)
Date: 2026-02-26

## Local Environment

```bash
# Install / upgrade modules in a local DB
./odoo-bin -d <db_name> -u open_sign,open_sign_web,open_sign_portal --stop-after-init

# Include optional certificate addon when needed
./odoo-bin -d <db_name> -u open_sign,open_sign_web,open_sign_portal,open_sign_certificate --stop-after-init
```

## Test Execution

```bash
# Core + portal Python tests
./odoo-bin -d <db_name> --test-enable --test-tags /open_sign,/open_sign_portal --stop-after-init

# Focused lifecycle test
./odoo-bin -d <db_name> --test-enable --test-tags open_sign.tests.test_sign_request_flow --stop-after-init

# Portal idempotency/security-focused tests
./odoo-bin -d <db_name> --test-enable --test-tags open_sign_portal.tests.test_portal_idempotency --stop-after-init
./odoo-bin -d <db_name> --test-enable --test-tags open_sign_portal.tests.test_portal_security --stop-after-init

# Frontend tests
./odoo-bin -d <db_name> --test-enable --test-tags /open_sign_web --stop-after-init
```

## Lint And Conformance

```bash
# Run lint-focused checks
./odoo-bin -d <db_name> --test-enable --test-tags /test_lint --stop-after-init

# Fast module structure sanity after edits
rg --files addons/open_sign addons/open_sign_web addons/open_sign_portal addons/open_sign_certificate
```

## Upgrade/Migration Checks

```bash
# Validate schema upgrade path
./odoo-bin -d <db_name> -u open_sign --stop-after-init

# Run regression suite after migration changes
./odoo-bin -d <db_name> --test-enable --test-tags /open_sign --stop-after-init
```

## Operational Validation (Pre-UAT)

```bash
# Verify cron jobs are loaded
./odoo-bin shell -d <db_name> <<'PY'
print(env['ir.cron'].search([('model_id.model', 'like', 'open.sign%')]).mapped('name'))
PY

# Verify access groups and model ACL load
./odoo-bin shell -d <db_name> <<'PY'
print(env['res.groups'].search([('name', 'ilike', 'Open Sign')]).mapped('name'))
PY
```

## Working Rules

- Always run module upgrade before functional tests when models/data XML changed.
- For portal endpoint changes, run `test_portal_security` and `test_portal_idempotency` before merge.
- For schema changes, update migration hooks and rerun focused upgrade tests.
