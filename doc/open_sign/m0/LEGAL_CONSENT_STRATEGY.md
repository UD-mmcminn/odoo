# Open Sign Legal Disclosure And Consent Strategy

Status: Finalized for M0 (`T96`)
Date: 2026-02-26

## Objective
Capture legally meaningful signer consent evidence at submit time, with deterministic storage and export behavior.

Baseline legal framework target for engineering controls:

- US ESIGN (federal priority)
- UETA (state-level alignment)

## Disclosure Strategy

- Consent text is rendered in portal submit flow immediately before signing action.
- Text source is versioned by template key and locale.
- Legal owners can update future text versions; historical requests retain original text hash.

## Evidence Captured Per Signer

- `consent_accepted_at` (server UTC)
- `consent_text_hash` (SHA-256 hash of rendered disclosure text)
- `signer_timezone` (optional presentation context)
- Associated audit events for submit/decline flow

## Consent Hashing Rules

- Normalize disclosure text before hashing:
  - Trim trailing spaces per line
  - Normalize line endings to `\n`
  - UTF-8 encoding
- Hash function: SHA-256 hex string

## Required Behavior

- Submit is rejected with `consent_required` unless explicit consent flag is true.
- Submitted `text_hash` must match server-rendered disclosure hash for signer context.
- Stored consent values are immutable once signer reaches `signed`.

## Localization

- Disclosure is localized for display, but hash is generated from exact rendered localized text.
- Export package includes locale and hash to support reproducibility.

## Legal Operations Notes

- This document finalizes strategy and evidence format.
- Jurisdiction-specific legal wording still requires Product/Legal signoff per governance process.
