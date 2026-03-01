import { expect, test } from "@odoo/hoot";

import {
    normalizeClientFieldValue,
    validateClientFieldValue,
} from "@open_sign_web/js/signing_form";

test("validateClientFieldValue accepts non-required fields", () => {
    const result = validateClientFieldValue({ required: false, type: "text" }, "");
    expect(result).toEqual({ valid: true, errorCode: null });
});

test("validateClientFieldValue rejects blank required value", () => {
    const result = validateClientFieldValue({ required: true, type: "text" }, " ");
    expect(result).toEqual({ valid: false, errorCode: "required_value_missing" });
});

test("required checkbox accepts both true and false booleans", () => {
    expect(validateClientFieldValue({ required: true, type: "checkbox" }, true)).toEqual({
        valid: true,
        errorCode: null,
    });
    expect(validateClientFieldValue({ required: true, type: "checkbox" }, false)).toEqual({
        valid: true,
        errorCode: null,
    });
});

test("checkbox rejects non-boolean payload", () => {
    const result = validateClientFieldValue({ required: true, type: "checkbox" }, "yes");
    expect(result).toEqual({ valid: false, errorCode: "invalid_checkbox_payload" });
});

test("normalizeClientFieldValue normalizes and validates email", () => {
    const result = normalizeClientFieldValue({ required: true, type: "email" }, "  ALICE@EXAMPLE.COM  ");
    expect(result.valid).toBe(true);
    expect(result.normalizedValue).toBe("alice@example.com");
});

test("normalizeClientFieldValue validates and normalizes phone", () => {
    const result = normalizeClientFieldValue({ required: true, type: "phone" }, " (555) 123-4567 ");
    expect(result.valid).toBe(true);
    expect(result.normalizedValue).toBe("5551234567");
});

test("normalizeClientFieldValue normalizes initials and enforces max length", () => {
    const valid = normalizeClientFieldValue({ required: true, type: "initials" }, " am ");
    expect(valid.valid).toBe(true);
    expect(valid.normalizedValue).toBe("AM");

    const invalid = normalizeClientFieldValue({ required: true, type: "initials" }, "ABCDEFGHI");
    expect(invalid).toEqual({
        valid: false,
        errorCode: "invalid_initials_length",
        normalizedValue: null,
        normalizedValueText: null,
        normalizedValueJson: null,
    });
});

test("text and multiline rules match server semantics", () => {
    const textWithNewline = validateClientFieldValue({ required: false, type: "text" }, "line1\nline2");
    expect(textWithNewline).toEqual({
        valid: false,
        errorCode: "single_line_newline_not_allowed",
    });

    const multiline = normalizeClientFieldValue({ required: true, type: "multiline" }, "line1\r\nline2\rline3");
    expect(multiline.valid).toBe(true);
    expect(multiline.normalizedValue).toBe("line1\nline2\nline3");
});

test("radio/selection values normalize to canonical option keys", () => {
    const field = {
        required: true,
        type: "selection",
        options: [{ value: "basic" }, { value: "pro" }],
    };
    const valid = normalizeClientFieldValue(field, " PRO ");
    expect(valid.valid).toBe(true);
    expect(valid.normalizedValue).toBe("pro");

    const invalid = validateClientFieldValue(field, "enterprise");
    expect(invalid).toEqual({
        valid: false,
        errorCode: "value_not_in_option_set",
    });
});

test("date values accept ISO string or object and reject invalid payloads", () => {
    const iso = normalizeClientFieldValue({ required: true, type: "date" }, "2026-03-01");
    expect(iso.valid).toBe(true);
    expect(iso.normalizedValue).toEqual({ iso_date: "2026-03-01" });

    const earlyIso = normalizeClientFieldValue({ required: true, type: "date" }, "0001-01-01");
    expect(earlyIso.valid).toBe(true);
    expect(earlyIso.normalizedValue).toEqual({ iso_date: "0001-01-01" });

    const obj = normalizeClientFieldValue(
        { required: true, type: "date" },
        { iso_date: "2026-03-02", timezone: "  UTC  " }
    );
    expect(obj.valid).toBe(true);
    expect(obj.normalizedValue).toEqual({ iso_date: "2026-03-02", timezone: "UTC" });

    const blank = validateClientFieldValue({ required: false, type: "date" }, "   ");
    expect(blank).toEqual({ valid: false, errorCode: "invalid_date_iso_format" });

    const invalid = validateClientFieldValue({ required: true, type: "date" }, "03/02/2026");
    expect(invalid).toEqual({ valid: false, errorCode: "invalid_date_iso_format" });

    const invalidCalendarDate = validateClientFieldValue(
        { required: true, type: "date" },
        "2026-02-31"
    );
    expect(invalidCalendarDate).toEqual({ valid: false, errorCode: "invalid_date_iso_format" });

    const invalidYearZero = validateClientFieldValue({ required: true, type: "date" }, "0000-01-01");
    expect(invalidYearZero).toEqual({ valid: false, errorCode: "invalid_date_iso_format" });
});

test("strikethrough requires boolean applied payload", () => {
    const valid = normalizeClientFieldValue({ required: true, type: "strikethrough" }, true);
    expect(valid.valid).toBe(true);
    expect(valid.normalizedValue).toEqual({ applied: true });

    const invalid = validateClientFieldValue(
        { required: true, type: "strikethrough" },
        { applied: "yes" }
    );
    expect(invalid).toEqual({ valid: false, errorCode: "invalid_strikethrough_payload" });
});

test("signature/stamp payload requires object and signed attachment when value present", () => {
    const missingAttachment = validateClientFieldValue(
        { required: true, type: "signature" },
        { method: "draw", display_name: "Alice" }
    );
    expect(missingAttachment).toEqual({
        valid: false,
        errorCode: "signed_payload_attachment_required",
    });

    const attachmentWithoutPayload = validateClientFieldValue(
        { required: true, type: "signature", signed_payload_attachment_id: 41 },
        false
    );
    expect(attachmentWithoutPayload).toEqual({
        valid: false,
        errorCode: "invalid_signature_payload",
    });

    const valid = normalizeClientFieldValue(
        { required: true, type: "signature" },
        {
            method: "draw",
            display_name: "Alice",
            signed_payload_attachment_id: 42,
        }
    );
    expect(valid.valid).toBe(true);
    expect(valid.normalizedValue.method).toBe("draw");
});

test("length and regex checks are applied for textual fields", () => {
    const field = {
        required: true,
        type: "text",
        minLength: 3,
        maxLength: 5,
        validationRegex: "^[A-Z0-9]+$",
    };

    expect(validateClientFieldValue(field, "AB")).toEqual({
        valid: false,
        errorCode: "value_too_short",
    });
    expect(validateClientFieldValue(field, "ABCDEF")).toEqual({
        valid: false,
        errorCode: "value_too_long",
    });
    expect(validateClientFieldValue(field, "ABC-")).toEqual({
        valid: false,
        errorCode: "value_does_not_match_pattern",
    });
    expect(validateClientFieldValue(field, "AB12")).toEqual({
        valid: true,
        errorCode: null,
    });
});

test("invalid validation regex pattern returns client error", () => {
    const result = validateClientFieldValue(
        { required: true, type: "text", validationRegex: "(" },
        "AB12"
    );
    expect(result).toEqual({
        valid: false,
        errorCode: "invalid_validation_pattern",
    });
});
