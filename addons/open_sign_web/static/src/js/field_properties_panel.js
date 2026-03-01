/** @odoo-module **/

export function normalizeFieldProperties(properties = {}) {
    return {
        required: Boolean(properties.required),
        placeholder: properties.placeholder || "",
        helpText: properties.helpText || "",
        defaultValue: properties.defaultValue ?? "",
    };
}
