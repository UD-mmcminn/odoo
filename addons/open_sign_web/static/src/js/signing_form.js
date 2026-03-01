/** @odoo-module **/

const EMPTY_RESULT = Object.freeze({ valid: true, errorCode: null });

export function validateClientFieldValue(field = {}, value) {
    if (!field.required) {
        return EMPTY_RESULT;
    }

    if (field.type === "checkbox") {
        return value
            ? EMPTY_RESULT
            : { valid: false, errorCode: "required_checkbox_unchecked" };
    }

    const normalized = String(value ?? "").trim();
    return normalized
        ? EMPTY_RESULT
        : { valid: false, errorCode: "required_value_missing" };
}
