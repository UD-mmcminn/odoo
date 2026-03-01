import { expect, test } from "@odoo/hoot";

import { validateClientFieldValue } from "@open_sign_web/js/signing_form";

test("validateClientFieldValue accepts non-required fields", () => {
    const result = validateClientFieldValue({ required: false, type: "text" }, "");
    expect(result).toEqual({ valid: true, errorCode: null });
});

test("validateClientFieldValue rejects unchecked required checkbox", () => {
    const result = validateClientFieldValue({ required: true, type: "checkbox" }, false);
    expect(result).toEqual({ valid: false, errorCode: "required_checkbox_unchecked" });
});

test("validateClientFieldValue rejects blank required value", () => {
    const result = validateClientFieldValue({ required: true, type: "text" }, " ");
    expect(result).toEqual({ valid: false, errorCode: "required_value_missing" });
});
