# Open Sign PDF Signing Stack Recommendation (v1)

Status: Finalized (`T05`)
Date: 2026-02-26

## Decision Scope
Pick implementation strategy for:
- Filling/flattening signer fields into a final PDF artifact
- Optional certificate-based digital signing
- US legal baseline support (`ESIGN` + `UETA` evidence requirements)

## Compliance Model (Engineering Baseline)
For ESIGN/UETA alignment, implementation should preserve:
- intent to sign (explicit signer action)
- consent to electronic records/signatures
- attribution (who signed, plus context)
- record integrity (tamper evidence over what was signed)
- retention/export capability

## What Odoo Already Provides

### Local code evidence in this repository
- `odoo/tools/pdf/signature.py` provides a `PdfSigner` class that:
  - adds a PDF signature field
  - computes ByteRange digest
  - produces CMS signature content (`sha256_rsa`)
- `odoo/addons/base/tests/test_signature.py` validates generated signature structure and digest behavior.

Inference:
- Odoo already has a cryptographic PDF-signature primitive that can be reused or mirrored in the optional certificate addon.

### Odoo Sign product guidance
- Odoo Sign documentation emphasizes legal validity criteria such as identity/authentication, integrity, and timestamping.

## External OSS References

- OpenSign (`OpenSignLabs/OpenSign`): AGPL project focused on document signing workflow and auditability.
- DocuSeal (`docusealco/docuseal`): open source e-sign platform with AGPL licensing and production signing workflows.
- pyHanko (`MatthiasValvekens/pyHanko`): Python toolkit for digitally signing and validating PDFs.

## Recommendation

### 1) Core addon (`open_sign`): electronic signature evidence + flattened final PDF
- Use Odoo-compatible PDF manipulation path for field placement/flattening.
- Persist source and final SHA-256 digests.
- Bind request to immutable template version before send.
- Keep this path independent from certificate signing complexity.

### 2) Optional addon (`open_sign_certificate`): cryptographic digital signature
- Use `pyHanko` for certificate-based PDF signing/validation.
- Keep certificate operations isolated to optional addon boundary.
- Sign only after final PDF is generated.

### 3) Contract for finalization pipeline
1. Validate request + signer completion.
2. Generate deterministic flattened PDF.
3. Compute `final_pdf_sha256`.
4. If certificate enabled, apply digital signature and persist certificate log.
5. Emit audit events and evidence package records.

## Why this is pragmatic
- Keeps MVP deliverable fast and legally defensible for ESIGN/UETA workflows.
- Avoids blocking core delivery on PKI/HSM complexity.
- Leaves room for stronger cryptographic controls in optional addon.

## Follow-Up Implementation Decisions
- Confirm PDF flattening library choice and exact license constraints.
- Confirm certificate key custody model (DB-stored key, external KMS/HSM, or both).
- Confirm whether timestamp authority (TSA) support is in MVP or post-MVP.

## References

- Odoo Sign documentation: https://www.odoo.com/documentation/19.0/applications/productivity/sign.html
- Odoo Sign product page: https://www.odoo.com/app/sign
- Odoo PDF signer utility in this repository: `/home/mmcminn/Projects/src/odoo/odoo/tools/pdf/signature.py`
- Odoo PDF signer tests in this repository: `/home/mmcminn/Projects/src/odoo/odoo/addons/base/tests/test_signature.py`
- OpenSign repository: https://github.com/OpenSignLabs/OpenSign
- DocuSeal repository: https://github.com/docusealco/docuseal
- pyHanko repository: https://github.com/MatthiasValvekens/pyHanko
