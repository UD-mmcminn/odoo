# Open Sign Legal/Compliance Acceptance Criteria (US Baseline)

Status: Finalized (`T03`)
Date: 2026-02-26

## Baseline
Engineering baseline aligns to US electronic signature frameworks:
- ESIGN (federal priority)
- UETA (state-level alignment)

## Acceptance Criteria

1. Intent to sign
- Submit action is explicit and user-driven.
- System records event `signer_submitted` with timestamp and actor context.

2. Consent to electronic signing
- Submit blocked unless consent checkbox is accepted.
- Consent text hash and acceptance timestamp are persisted.

3. Attribution
- Signer identity context captured (email, signer role, token-scoped signer id).
- Signer interaction metadata captured (IP/user agent where available).

4. Integrity of signed record
- Request binds to immutable template version before send.
- Source and final PDF SHA-256 digests are stored.
- Audit trail is append-only and hash-chain verifiable.

5. Record retention and reproducibility
- Evidence package export available.
- Stored evidence includes signers, values, timeline, consent hash, and artifact digests.

## Governance Boundary

- Engineering implements evidentiary controls above.
- Jurisdiction-specific legal text and policy approval is handled by Legal/Compliance owners.
