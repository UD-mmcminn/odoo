/** @odoo-module **/

const FIELD_TYPES_WITH_OPTIONS = new Set(["radio", "selection"]);
const FIELD_TYPES_WITH_LENGTH_BOUNDS = new Set([
    "text",
    "multiline",
    "name",
    "email",
    "phone",
    "company",
]);
const DEFAULT_FIELD_TYPE = "text";

function asOptionalInteger(value) {
    if (value === "" || value === null || value === undefined) {
        return null;
    }
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : null;
}

export function sanitizeFieldLabel(value, fallback = "Field") {
    const normalized = String(value || "").trim();
    return normalized || fallback;
}

export function normalizeFieldProperties(properties = {}, fieldType = "text") {
    let minLength = asOptionalInteger(properties.minLength);
    let maxLength = asOptionalInteger(properties.maxLength);
    const sequence = Math.max(0, asOptionalInteger(properties.sequence) ?? 10);

    if (minLength !== null && minLength < 0) {
        minLength = 0;
    }
    if (maxLength !== null && maxLength < 0) {
        maxLength = 0;
    }
    if (minLength !== null && maxLength !== null && minLength > maxLength) {
        maxLength = minLength;
    }

    if (!FIELD_TYPES_WITH_LENGTH_BOUNDS.has(fieldType)) {
        minLength = null;
        maxLength = null;
    }

    const optionList = FIELD_TYPES_WITH_OPTIONS.has(fieldType)
        ? String(properties.optionList || "")
              .split("\n")
              .map((value) => value.trim())
              .filter(Boolean)
              .join("\n")
        : "";

    return {
        required: Boolean(properties.required),
        sequence,
        placeholder: String(properties.placeholder || "").trim(),
        helpText: String(properties.helpText || "").trim(),
        defaultValue: String(properties.defaultValue ?? ""),
        validationRegex: String(properties.validationRegex || "").trim(),
        minLength,
        maxLength,
        optionList,
    };
}

export function toTemplateFieldVals(field = {}) {
    const type = field.type || DEFAULT_FIELD_TYPE;
    const roleId = asOptionalInteger(field.roleId ?? field.role_id);
    const normalized = normalizeFieldProperties(field, type);
    const optionValues = supportsFieldOptions(type)
        ? normalized.optionList
              .split("\n")
              .map((value) => value.trim())
              .filter(Boolean)
        : [];
    const optionIds = optionValues.map((value, index) => [
        0,
        0,
        {
            value,
            label: value,
            sequence: (index + 1) * 10,
        },
    ]);

    return {
        role_id: roleId || false,
        type,
        label: sanitizeFieldLabel(field.label, "Field"),
        required: normalized.required,
        sequence: normalized.sequence,
        default_value: normalized.defaultValue,
        validation_regex: normalized.validationRegex,
        min_length: normalized.minLength,
        max_length: normalized.maxLength,
        option_ids: optionIds,
    };
}

export function supportsFieldOptions(fieldType) {
    return FIELD_TYPES_WITH_OPTIONS.has(fieldType);
}

export function supportsLengthBounds(fieldType) {
    return FIELD_TYPES_WITH_LENGTH_BOUNDS.has(fieldType);
}
