import { expect, test } from "@odoo/hoot";

import {
    normalizeFieldProperties,
    sanitizeFieldLabel,
    supportsFieldOptions,
    supportsLengthBounds,
    toTemplateFieldVals,
} from "@open_sign_web/js/field_properties_panel";

test("normalizeFieldProperties applies scalar normalization and bounds", () => {
    const normalized = normalizeFieldProperties(
        {
            required: 1,
            sequence: -2,
            minLength: 10,
            maxLength: 5,
            placeholder: "  hello  ",
            helpText: "  help text  ",
            validationRegex: "  ^[a-z]+$  ",
        },
        "text"
    );

    expect(normalized).toEqual({
        required: true,
        sequence: 0,
        placeholder: "hello",
        helpText: "help text",
        defaultValue: "",
        validationRegex: "^[a-z]+$",
        minLength: 10,
        maxLength: 10,
        optionList: "",
    });
});

test("normalizeFieldProperties clears unsupported option and length fields", () => {
    const checkbox = normalizeFieldProperties(
        {
            optionList: "A\nB",
            minLength: 1,
            maxLength: 2,
        },
        "checkbox"
    );

    expect(checkbox.optionList).toBe("");
    expect(checkbox.minLength).toBe(null);
    expect(checkbox.maxLength).toBe(null);
});

test("normalizeFieldProperties keeps option list for option-based fields", () => {
    const selection = normalizeFieldProperties(
        {
            optionList: "  Option 1 \n\n Option 2\n",
        },
        "selection"
    );

    expect(selection.optionList).toBe("Option 1\nOption 2");
});

test("sanitizeFieldLabel returns fallback for empty values", () => {
    expect(sanitizeFieldLabel("  ", "Field 42")).toBe("Field 42");
    expect(sanitizeFieldLabel("  Sign Here  ", "Fallback")).toBe("Sign Here");
});

test("field-type capability helpers expose expected behavior", () => {
    expect(supportsFieldOptions("selection")).toBe(true);
    expect(supportsFieldOptions("text")).toBe(false);
    expect(supportsLengthBounds("text")).toBe(true);
    expect(supportsLengthBounds("checkbox")).toBe(false);
});

test("toTemplateFieldVals maps editor state to backend-safe keys", () => {
    const vals = toTemplateFieldVals({
        type: "selection",
        label: "  Approver Choice  ",
        required: true,
        sequence: 42,
        defaultValue: "A",
        validationRegex: "  ^[A-Z]$  ",
        minLength: 1,
        maxLength: 2,
        optionList: " A \n\nB ",
        placeholder: "editor only",
        helpText: "editor only",
    });

    expect(vals).toEqual({
        type: "selection",
        label: "Approver Choice",
        required: true,
        sequence: 42,
        default_value: "A",
        validation_regex: "^[A-Z]$",
        min_length: null,
        max_length: null,
        option_ids: [
            [0, 0, { value: "A", label: "A", sequence: 10 }],
            [0, 0, { value: "B", label: "B", sequence: 20 }],
        ],
    });
});
