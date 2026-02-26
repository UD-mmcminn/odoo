# Open Sign Field Validation Test Vectors (v1)

Status: Finalized for M0 (`T98`)
Date: 2026-02-26

## Purpose
Provide canonical valid/invalid examples to keep client/server validators aligned.

## Test Vectors

| Field Type | Case | Input | Expected Result | Normalized Output |
|---|---|---|---|---|
| `email` | valid | `Alice.Example@Domain.com` | pass | `alice.example@domain.com` |
| `email` | invalid | `alice@@domain` | fail (`validation_error`) | n/a |
| `phone` | valid | `+1 (555) 010-2020` | pass | `+15550102020` |
| `phone` | invalid | `abc123` | fail (`validation_error`) | n/a |
| `text` | valid | `Purchase Order #91` | pass | `Purchase Order #91` |
| `text` | invalid | `line1\nline2` | fail (`validation_error`) | n/a |
| `multiline` | valid | `line1\r\nline2` | pass | `line1\nline2` |
| `checkbox` | valid | `true` | pass | `true` |
| `checkbox` | invalid | `"yes"` | fail (`validation_error`) | n/a |
| `radio` | valid | `"opt_standard"` | pass (if option exists) | `opt_standard` |
| `radio` | invalid | `"not_in_options"` | fail (`validation_error`) | n/a |
| `selection` | valid | `"choice_b"` | pass (if option exists) | `choice_b` |
| `date` | valid | `"2026-02-26"` | pass | `{ "iso_date": "2026-02-26" }` |
| `date` | invalid | `"26/02/2026"` | fail (`validation_error`) | n/a |
| `initials` | valid | `am` | pass | `AM` |
| `initials` | invalid | `ABCDEFGHI` | fail (`validation_error`) | n/a |
| `signature` | valid | draw payload + PNG attachment | pass | JSON metadata + attachment ref |
| `signature` | invalid | missing payload and attachment | fail (`validation_error`) | n/a |
| `stamp` | valid | PNG stamp upload | pass | JSON metadata + attachment ref |
| `stamp` | invalid | unsupported mimetype (`text/plain`) | fail (`validation_error`) | n/a |
| `strikethrough` | valid | `{ "applied": true }` | pass | `{ "applied": true }` |
| `strikethrough` | invalid | `{ "applied": "yes" }` | fail (`validation_error`) | n/a |

## Enforcement Notes

- Server-side validator is authoritative.
- Client-side validator mirrors server rules for UX only.
- Any matrix change must update both tests and `FEATURE.md` matrix sections.
