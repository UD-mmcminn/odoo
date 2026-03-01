/** @odoo-module **/

export const FIELD_PALETTE_TYPES = Object.freeze([
    "text",
    "textarea",
    "signature",
    "initial",
    "checkbox",
    "selection",
    "date",
]);

export function buildPaletteEntry(type, label) {
    return {
        type,
        label: label || type,
    };
}
