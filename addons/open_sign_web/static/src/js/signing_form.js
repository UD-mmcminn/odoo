/** @odoo-module **/

const EMPTY_RESULT = Object.freeze({ valid: true, errorCode: null });
const FIELD_TYPES_TEXTUAL = new Set([
    "initials",
    "name",
    "email",
    "phone",
    "company",
    "text",
    "multiline",
    "radio",
    "selection",
]);
const FIELD_TYPES_JSON_BOOL = new Set(["checkbox"]);
const FIELD_TYPES_JSON_DICT = new Set(["signature", "stamp"]);
const FIELD_TYPES_DATE = new Set(["date"]);
const FIELD_TYPES_STRIKETHROUGH = new Set(["strikethrough"]);
const FIELD_TYPES_WITH_OPTIONS = new Set(["radio", "selection"]);
const CONTROL_CHARS_RE = /[\x00-\x08\x0B-\x1F\x7F]/;
const PHONE_RE = /^\+?[0-9]{7,20}$/;
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function asString(value) {
    if (value === false || value === null || value === undefined) {
        return "";
    }
    return String(value);
}

function normalizeNewlines(value) {
    return asString(value).replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

function isPresent(value) {
    if (value === false || value === null || value === undefined) {
        return false;
    }
    if (typeof value === "string") {
        return Boolean(value.trim());
    }
    if (typeof value === "object") {
        return Boolean(Object.keys(value).length);
    }
    return true;
}

function getFieldType(field) {
    return field.type || "text";
}

function getFieldMinLength(field) {
    const value = Number.parseInt(field.minLength ?? field.min_length, 10);
    return Number.isInteger(value) && value > 0 ? value : 0;
}

function getFieldMaxLength(field) {
    const value = Number.parseInt(field.maxLength ?? field.max_length, 10);
    return Number.isInteger(value) && value > 0 ? value : 0;
}

function getFieldRegex(field) {
    return asString(field.validationRegex ?? field.validation_regex).trim();
}

function collectOptionValues(field) {
    const values = [];
    const pushValue = (candidate) => {
        const normalized = asString(candidate).trim();
        if (normalized) {
            values.push(normalized);
        }
    };

    const optionList = field.optionList;
    if (typeof optionList === "string") {
        for (const value of optionList.split("\n")) {
            pushValue(value);
        }
    }

    for (const key of ["optionValues", "options", "option_ids", "optionIds"]) {
        const options = field[key];
        if (!Array.isArray(options)) {
            continue;
        }
        for (const option of options) {
            if (option && typeof option === "object") {
                if ("value" in option) {
                    pushValue(option.value);
                } else if (Array.isArray(option) && option[2] && typeof option[2] === "object") {
                    pushValue(option[2].value);
                } else if (Array.isArray(option)) {
                    pushValue(option[0]);
                }
            } else {
                pushValue(option);
            }
        }
    }

    return values;
}

function normalizeOptionValue(field, value) {
    const normalizedInput = asString(value).trim();
    if (!normalizedInput) {
        return { value: false, errorCode: null };
    }
    const options = collectOptionValues(field);
    const canonicalByLower = new Map(options.map((option) => [option.toLowerCase(), option]));
    const canonical = canonicalByLower.get(normalizedInput.toLowerCase());
    if (!canonical) {
        return { value: null, errorCode: "value_not_in_option_set" };
    }
    return { value: canonical, errorCode: null };
}

function normalizePhone(value) {
    let normalized = asString(value).trim().replace(/[\s().-]+/g, "");
    if (normalized.startsWith("00")) {
        normalized = `+${normalized.slice(2)}`;
    }
    if (!PHONE_RE.test(normalized)) {
        return { value: null, errorCode: "invalid_phone" };
    }
    return { value: normalized, errorCode: null };
}

function normalizeDateValue(value) {
    const parseIsoDate = (candidate) => {
        if (!ISO_DATE_RE.test(candidate)) {
            return false;
        }
        const [year] = candidate.split("-").map((part) => Number.parseInt(part, 10));
        if (!Number.isInteger(year) || year < 1) {
            return false;
        }
        const parsed = new Date(`${candidate}T00:00:00Z`);
        return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === candidate;
    };

    if (typeof value === "string") {
        const isoDate = value.trim();
        if (!parseIsoDate(isoDate)) {
            return { value: null, errorCode: "invalid_date_iso_format" };
        }
        return { value: { iso_date: isoDate }, errorCode: null };
    }
    if (value && typeof value === "object" && !Array.isArray(value)) {
        const isoDate = asString(value.iso_date || value.isoDate).trim();
        if (!parseIsoDate(isoDate)) {
            return { value: null, errorCode: "invalid_date_iso_format" };
        }
        const normalized = { iso_date: isoDate };
        const timezone = asString(value.timezone).trim();
        if (timezone) {
            normalized.timezone = timezone;
        }
        return { value: normalized, errorCode: null };
    }
    return { value: null, errorCode: "invalid_date_payload" };
}

function normalizeStrikethroughValue(value) {
    if (typeof value === "boolean") {
        return { value: { applied: value }, errorCode: null };
    }
    if (value && typeof value === "object" && typeof value.applied === "boolean") {
        return { value: { applied: value.applied }, errorCode: null };
    }
    return { value: null, errorCode: "invalid_strikethrough_payload" };
}

function normalizeSignatureOrStampValue(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        return { value: null, errorCode: "invalid_signature_payload" };
    }
    return { value, errorCode: null };
}

function getSignedPayloadAttachment(field, normalizedJson) {
    return (
        field.signedPayloadAttachmentId ||
        field.signed_payload_attachment_id ||
        (normalizedJson && normalizedJson.signedPayloadAttachmentId) ||
        (normalizedJson && normalizedJson.signed_payload_attachment_id) ||
        false
    );
}

function applyLengthAndRegexRules(field, normalizedText) {
    if (!isPresent(normalizedText)) {
        return EMPTY_RESULT;
    }
    const minLength = getFieldMinLength(field);
    const maxLength = getFieldMaxLength(field);
    const length = normalizedText.length;
    if (minLength > 0 && length < minLength) {
        return { valid: false, errorCode: "value_too_short" };
    }
    if (maxLength > 0 && length > maxLength) {
        return { valid: false, errorCode: "value_too_long" };
    }
    const validationPattern = getFieldRegex(field);
    if (validationPattern) {
        let compiledPattern = null;
        try {
            compiledPattern = new RegExp(`^(?:${validationPattern})$`);
        } catch {
            return { valid: false, errorCode: "invalid_validation_pattern" };
        }
        if (!compiledPattern.test(normalizedText)) {
            return { valid: false, errorCode: "value_does_not_match_pattern" };
        }
    }
    return EMPTY_RESULT;
}

function normalizeTextualValue(field, value) {
    const fieldType = getFieldType(field);
    if (value === false || value === null || value === undefined) {
        return { value: false, errorCode: null };
    }
    const rawText = asString(value);

    if (fieldType === "multiline") {
        const normalized = normalizeNewlines(rawText).replace(/^\n+|\n+$/g, "");
        if (!normalized.trim()) {
            return { value: false, errorCode: null };
        }
        if (CONTROL_CHARS_RE.test(normalized)) {
            return { value: null, errorCode: "control_chars_not_allowed" };
        }
        return { value: normalized, errorCode: null };
    }

    const normalized = rawText.trim();
    if (!normalized) {
        return { value: false, errorCode: null };
    }

    if (fieldType === "email") {
        const canonical = normalized.toLowerCase();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(canonical)) {
            return { value: null, errorCode: "invalid_email" };
        }
        if (canonical.length > 254) {
            return { value: null, errorCode: "email_too_long" };
        }
        return { value: canonical, errorCode: null };
    }

    if (fieldType === "phone") {
        return normalizePhone(normalized);
    }

    if (fieldType === "initials") {
        const initials = normalized.toUpperCase();
        if (initials.length < 1 || initials.length > 8) {
            return { value: null, errorCode: "invalid_initials_length" };
        }
        return { value: initials, errorCode: null };
    }

    if (FIELD_TYPES_WITH_OPTIONS.has(fieldType)) {
        return normalizeOptionValue(field, normalized);
    }

    if (fieldType === "text" && normalized.includes("\n")) {
        return { value: null, errorCode: "single_line_newline_not_allowed" };
    }

    if (["name", "company", "text"].includes(fieldType) && CONTROL_CHARS_RE.test(normalized)) {
        return { value: null, errorCode: "control_chars_not_allowed" };
    }

    return { value: normalized, errorCode: null };
}

export function normalizeClientFieldValue(field = {}, value) {
    const fieldType = getFieldType(field);
    let normalizedText = value;
    let normalizedJson = value;

    if (FIELD_TYPES_TEXTUAL.has(fieldType)) {
        const normalization = normalizeTextualValue(field, value);
        if (normalization.errorCode) {
            return {
                valid: false,
                errorCode: normalization.errorCode,
                normalizedValue: null,
                normalizedValueText: null,
                normalizedValueJson: null,
            };
        }
        normalizedText = normalization.value;
        normalizedJson = false;
        const rulesResult = applyLengthAndRegexRules(field, normalizedText);
        if (!rulesResult.valid) {
            return {
                valid: false,
                errorCode: rulesResult.errorCode,
                normalizedValue: null,
                normalizedValueText: null,
                normalizedValueJson: null,
            };
        }
    } else if (FIELD_TYPES_JSON_BOOL.has(fieldType)) {
        normalizedText = false;
        if (typeof value !== "boolean") {
            if (value === null || value === undefined || value === false) {
                normalizedJson = false;
            } else {
                return {
                    valid: false,
                    errorCode: "invalid_checkbox_payload",
                    normalizedValue: null,
                    normalizedValueText: null,
                    normalizedValueJson: null,
                };
            }
        } else {
            normalizedJson = value;
        }
    } else if (FIELD_TYPES_DATE.has(fieldType)) {
        normalizedText = false;
        if (value === null || value === undefined || value === false) {
            normalizedJson = false;
        } else {
            const normalization = normalizeDateValue(value);
            if (normalization.errorCode) {
                return {
                    valid: false,
                    errorCode: normalization.errorCode,
                    normalizedValue: null,
                    normalizedValueText: null,
                    normalizedValueJson: null,
                };
            }
            normalizedJson = normalization.value;
        }
    } else if (FIELD_TYPES_STRIKETHROUGH.has(fieldType)) {
        normalizedText = false;
        if (value === null || value === undefined || value === false) {
            normalizedJson = false;
        } else {
            const normalization = normalizeStrikethroughValue(value);
            if (normalization.errorCode) {
                return {
                    valid: false,
                    errorCode: normalization.errorCode,
                    normalizedValue: null,
                    normalizedValueText: null,
                    normalizedValueJson: null,
                };
            }
            normalizedJson = normalization.value;
        }
    } else if (FIELD_TYPES_JSON_DICT.has(fieldType)) {
        normalizedText = false;
        if (value === null || value === undefined || value === false) {
            normalizedJson = false;
        } else {
            const normalization = normalizeSignatureOrStampValue(value);
            if (normalization.errorCode) {
                return {
                    valid: false,
                    errorCode: normalization.errorCode,
                    normalizedValue: null,
                    normalizedValueText: null,
                    normalizedValueJson: null,
                };
            }
            normalizedJson = normalization.value;
        }
    }

    const payloadAttachment = FIELD_TYPES_JSON_DICT.has(fieldType)
        ? getSignedPayloadAttachment(field, normalizedJson)
        : false;
    let hasValue = isPresent(normalizedText) || isPresent(normalizedJson) || Boolean(payloadAttachment);
    if (fieldType === "checkbox" && typeof value === "boolean") {
        hasValue = true;
    }
    if (field.required && !hasValue) {
        return {
            valid: false,
            errorCode: "required_value_missing",
            normalizedValue: null,
            normalizedValueText: null,
            normalizedValueJson: null,
        };
    }

    if (FIELD_TYPES_JSON_DICT.has(fieldType) && hasValue) {
        if (!isPresent(normalizedJson)) {
            return {
                valid: false,
                errorCode: "invalid_signature_payload",
                normalizedValue: null,
                normalizedValueText: null,
                normalizedValueJson: null,
            };
        }
        if (!payloadAttachment) {
            return {
                valid: false,
                errorCode: "signed_payload_attachment_required",
                normalizedValue: null,
                normalizedValueText: null,
                normalizedValueJson: null,
            };
        }
    }

    return {
        valid: true,
        errorCode: null,
        normalizedValue: FIELD_TYPES_TEXTUAL.has(fieldType) ? normalizedText : normalizedJson,
        normalizedValueText: normalizedText,
        normalizedValueJson: normalizedJson,
    };
}

export function validateClientFieldValue(field = {}, value) {
    const result = normalizeClientFieldValue(field, value);
    return { valid: result.valid, errorCode: result.errorCode };
}
