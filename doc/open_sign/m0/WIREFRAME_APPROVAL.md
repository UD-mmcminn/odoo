# Open Sign Wireframe Approval Pack (v1)

Status: Finalized (`T04`)
Date: 2026-02-26

## Objective
Define the MVP screen flows for:
- Internal template editor
- Internal request lifecycle (`draft -> versioned -> sent`)
- Public signer portal

## Workflow Summary

```text
Template Draft -> Template Published -> Request Draft -> Request Versioned (immutable snapshot) -> Sent -> Signer Actions -> Completed/Declined/Expired
```

## Screen List

1. Template list (internal)
2. Template editor canvas (internal)
3. Template version modal (internal)
4. Request compose/send form (internal)
5. Request detail timeline (internal)
6. Portal signer page (public)
7. Portal submit/decline confirmation (public)

## Wireframes

### 1) Template Editor Canvas (Desktop)

```text
+-----------------------------------------------------------------------------------+
| Open Sign / Templates / [NDA v3]                                  [Save] [Publish]|
+-------------------------+-----------------------------------------+----------------+
| Field Palette           | PDF Canvas (Page 1/8)                   | Properties     |
|-------------------------|                                         |----------------|
| Signature               |  +-----------------------------------+  | Label: [Name ] |
| Initials                |  |                                   |  | Type: text     |
| Name                    |  | [Name Field Box]                  |  | Required: [x]  |
| Email                   |  |                                   |  | Role: [Buyer]  |
| Phone                   |  | [Signature Box]                   |  | Min/Max: 1/64  |
| Company                 |  |                                   |  | Regex: [...]   |
| Text                    |  +-----------------------------------+  | Default: [...] |
| Multiline               |                                         |                |
| Checkbox                | Role chips: [Seller] [Buyer] [Witness] | [Delete Field] |
| Radio / Selection       | Zoom [-] 100% [+]  Grid [x] Snap [x]   |                |
| Date                    |                                         |                |
| Strikethrough / Stamp   |                                         |                |
+-------------------------+-----------------------------------------+----------------+
```

### 2) Publish Version Modal (Template -> Immutable Version)

```text
+-------------------------------------------------------------+
| Publish Template Version                                    |
+-------------------------------------------------------------+
| Template: NDA v3                                            |
| Next Version: 4                                             |
| Source PDF Digest: 9f...a1 (SHA-256)                        |
| Snapshot includes: roles + fields + options + geometry      |
|                                                             |
| [ ] Confirm this version becomes immutable once published    |
|                                                             |
|                                   [Cancel] [Publish Version] |
+-------------------------------------------------------------+
```

### 3) Request Compose / Send (Internal)

```text
+--------------------------------------------------------------------------------+
| New Signature Request                                           [Save Draft]    |
+--------------------------------------------------------------------------------+
| Template: [NDA v3]  Version: [4 immutable]                                     |
| Request Name: [Acme Master Service Agreement]                                  |
| Ordered Signing: [x]                                                            |
| Expires At: [2026-04-30 23:59 UTC]                                              |
|                                                                                |
| Signers                                                                        |
| 1. Buyer Role    Email: [buyer@acme.com]                                       |
| 2. Seller Role   Email: [legal@vendor.com]                                     |
|                                                                                |
| Actions: [Version Request] [Send for Signature]                                |
+--------------------------------------------------------------------------------+
```

### 4) Request Detail / Timeline (Internal)

```text
+--------------------------------------------------------------------------------+
| Request: Acme MSA                                 Status: IN_PROGRESS           |
+--------------------------------------------------------------------------------+
| Version: 4 (immutable)   Source Digest: 9f...a1   Final Digest: --             |
|                                                                                |
| Timeline                                                                       |
| - Request created (2026-02-26T13:01:00Z)                                      |
| - Request versioned (v4, digest 9f...a1)                                      |
| - Request sent                                                                  |
| - Buyer opened link (IP, UA)                                                   |
| - Field value updated: Company Name                                            |
| - Signature applied                                                             |
+--------------------------------------------------------------------------------+
```

### 5) Signer Portal (Desktop)

```text
+--------------------------------------------------------------------------------+
| Document: Acme MSA                                      Step 1 of 2 signers     |
+--------------------------------------------------------------------------------+
| [PDF Preview with overlays and required markers * ]                            |
|                                                                                |
| Required fields left: 3                                                        |
| [Save Draft]                                               [Decline] [Submit]   |
+--------------------------------------------------------------------------------+
| Consent                                                                    [x]  |
| I agree to sign electronically and confirm intent to sign this document.       |
| (Disclosure text localized; consent hash tied to submission)                    |
+--------------------------------------------------------------------------------+
```

### 6) Signer Portal (Mobile)

```text
+-----------------------------+
| Acme MSA        Step 1/2    |
+-----------------------------+
| [PDF page viewport]         |
| [Next required field]       |
|                             |
| [Save] [Decline] [Submit]   |
+-----------------------------+
| Consent [x]                 |
| intent + e-sign disclosure  |
+-----------------------------+
```

## Interaction Rules

- `Send for Signature` is disabled until request is `versioned`.
- `Version Request` creates immutable binding to `open.sign.template.version`.
- Required field completion blocks submit until satisfied.
- Submit must include explicit consent acceptance.
- Save/submit/decline are token-gated in portal.

## Approval Checklist

- [x] Workflow approved (`draft -> versioned -> sent`).
- [x] Template editor wireframe approved.
- [x] Signer portal wireframe approved (desktop + mobile).
- [x] Consent placement and wording strategy approved.
- [x] Request timeline evidence display approved.

## Reviewer Signoff

- Product: M McMinn
- Engineering: M McMinn
- Legal/Compliance: M McMinn
- Date: 2026/02/26
