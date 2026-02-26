# Open Sign M0 Design Data Collection Notes

Status: Finalized for M0 (`T90`)
Date: 2026-02-26
Owner: Engineering

## Summary
This document records concrete design findings from the Odoo reference map in `FEATURE.md` and translates them into implementation rules for the `open_sign*` addons.

## Reference Findings

| Area | References | Findings | Open Sign Rule |
|---|---|---|---|
| Portal token model | `addons/portal/models/portal_mixin.py` | `portal.mixin` provides `access_token`, `_portal_ensure_token()`, and URL helpers. | `open.sign.request.signer` must inherit `portal.mixin` in portal addon. |
| Portal access guard | `addons/portal/controllers/portal.py` | `_document_check_access()` validates access tokens and uses `consteq`. | All public signer routes must use token-guard access checks and constant-time token compare behavior. |
| Signature portal flow | `addons/sale/controllers/portal.py` | `jsonrpc` accept/decline endpoints use token access and state checks before writes. | Use `jsonrpc` submit/decline/save endpoints with explicit state gating + idempotency controls. |
| Reusable signature UI | `addons/portal/static/src/signature_form/*` | Existing signature form supports draw/type UX and portal-friendly wiring. | Reuse portal signature UX patterns where practical; only custom-build where feature gap exists. |
| Manifest conventions | `odoo/addons/test_lint/tests/test_manifests.py`, `addons/sale/__manifest__.py` | Manifest keys/order and asset declarations are linted. | Keep manifests strict: valid keys only, ordered data loading, assets in manifest not `views/assets.xml`. |
| Module/test structure | `odoo/addons/test_lint/tests/test_dunderinit.py`, `test_test_holes.py`, `addons/sale/tests/__init__.py` | Missing `__init__.py` or unimported tests are lint failures. | Every package and test package must have `__init__.py` and explicit test imports. |
| ACL/rule patterns | `addons/sale/security/*`, `addons/hr/security/hr_security.xml` | ACL CSV + record rules + group layering are standard. | Keep ACL matrix explicit in CSV; enforce company and ownership rules in XML record rules. |
| Model field conventions | `addons/sale/models/sale_order.py`, `addons/account/models/account_move.py` | Tracking/index/check-company conventions are broadly used. | Use indexed Many2one fields, consistent status selections, and `check_company=True` where applicable. |
| Test styles | `addons/sale/tests/test_controllers.py`, `test_access_rights.py` | `HttpCase` + security/access tests are standard for portals. | Implement unit + integration + HTTP security tests per phase. |
| Binary/tokenized access | `addons/web/controllers/binary.py`, `addons/mail/models/ir_attachment.py` | Attachment access control relies on scoped tokens. | Signed artifacts and payload attachments require token-scoped access policy with expiry. |
| Chatter/audit patterns | `addons/mail/models/mail_thread.py`, `mail_message.py` | Message/event models and tracking patterns are append-oriented. | Audit log must be append-only with hash chain + event sequence. |
| API/lint constraints | `test_naming.py`, `test_orm_import.py`, `test_override_signatures.py` | No public args named `ids`/`context`; no `odoo.orm` imports; override signatures enforced. | Enforce lint-safe API signatures/import style from day 1. |
| Index and SQL expectations | `odoo/addons/test_lint/tests/test_index.py` | One2many inverse fields should be btree indexed (`btree` / `btree_not_null`). | Index inverse relations and key status/filter fields in schema contract. |
| i18n rules | `test_jstranslate.py`, `test_i18n.py` | JS translations require `_t`; component props need `.translate`. | User-facing JS/XML strings must follow translation rules in all new UI code. |
| Migration conventions | Existing module migration folders and upgrade scripts | Upgrade scripts are expected for schema evolution. | Add migration hooks/scripts as first-class deliverable (`T112`). |
| Retry/idempotency patterns | `addons/payment/models/payment_transaction.py`, `addons/portal/tests/test_addresses.py` | Safe retries and deterministic behavior are expected in stateful flows. | Add explicit idempotency key registry and race-condition tests for submit/decline. |
| UTC datetime handling | `addons/mail/models/mail_mail.py`, `addons/mail/models/mail_template.py` | Canonical UTC storage is expected. | Persist evidence timestamps in UTC and render in user timezone only at presentation layer. |
| PDF signing internals | `odoo/tools/pdf/signature.py` | Odoo has PDF signature internals suitable for optional certificate extension. | Keep certificate signing optional and isolated in `open_sign_certificate`. |

## Decisions Locked For M0

- Use `portal.mixin` token model and `_document_check_access` style access guard patterns.
- Keep schema and workflow logic in `open_sign`; UI and portal flows in dedicated addons.
- Enforce idempotency and race safety for mutating portal signer endpoints.
- Enforce UTC evidence timestamps and immutable SHA-256 artifact digests.
- Keep XML `noupdate` policy explicit by record category.

## Output Artifacts Generated In M0

- `FEATURE.md` updates for requirements `R-024` to `R-028`.
- `doc/open_sign/m0/SECURITY_ACL_POLICY.md`
- `doc/open_sign/m0/PORTAL_API_CONTRACT.md`
- `doc/open_sign/m0/LEGAL_CONSENT_STRATEGY.md`
- `doc/open_sign/m0/ATTACHMENT_ACCESS_POLICY.md`
- `doc/open_sign/m0/VALIDATION_TEST_VECTORS.md`
- `doc/open_sign/m0/EVIDENCE_SCHEMA_V1.md`
