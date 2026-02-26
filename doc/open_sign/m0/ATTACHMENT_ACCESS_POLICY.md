# Open Sign Signed Attachment Access Policy

Status: Finalized for M0 (`T97`)
Date: 2026-02-26

## Scope

- Source template PDFs
- Signed payload attachments (signature/stamp uploads)
- Final signed PDFs
- Exported evidence packages

## Access Principles

- Least privilege by default.
- Portal signers must not gain broad model access; downloads are token-scoped.
- Internal users follow ACL + record rule + company isolation.

## Token Scope Policy

- Portal download links include signer/request scoped token context.
- Tokens must be validated using constant-time comparison semantics.
- Tokens are rejected if request/signer is expired, revoked, or outside allowed state.

## Visibility Matrix

| Artifact | Internal User | Manager | Auditor | Portal Signer |
|---|---|---|---|---|
| Source PDF | R (request scope) | R/W | R | No direct access |
| Signer payload attachment | R (request scope) | R/W | R | Only own signer-context payload when needed |
| Final signed PDF | R (request scope) | R/W | R | R via scoped token link |
| Evidence package export | R (policy scope) | R/W | R | Not public by default |

## Expiry And Revocation

- Tokenized download access follows request lifecycle and configured expiry windows.
- Revoked tokens immediately invalidate existing links.
- Completed request artifacts remain accessible only via role-appropriate access paths.

## Integrity Rules

- Final PDF digest (`final_pdf_sha256`) must be verified during evidence export.
- Source digest (`source_pdf_sha256`) must remain immutable for the request lifecycle.

## Logging

- Artifact downloads generate `artifact_downloaded` audit events with actor and access mode metadata.
