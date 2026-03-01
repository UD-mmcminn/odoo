/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

const PALETTE_ENTRIES = Object.freeze([
    Object.freeze({ type: "signature", label: _t("Signature"), defaultWidth: 0.3, defaultHeight: 0.12 }),
    Object.freeze({ type: "initials", label: _t("Initials"), defaultWidth: 0.18, defaultHeight: 0.1 }),
    Object.freeze({ type: "name", label: _t("Full Name"), defaultWidth: 0.3, defaultHeight: 0.08 }),
    Object.freeze({ type: "email", label: _t("Email"), defaultWidth: 0.34, defaultHeight: 0.08 }),
    Object.freeze({ type: "phone", label: _t("Phone"), defaultWidth: 0.28, defaultHeight: 0.08 }),
    Object.freeze({ type: "company", label: _t("Company"), defaultWidth: 0.34, defaultHeight: 0.08 }),
    Object.freeze({ type: "text", label: _t("Text"), defaultWidth: 0.32, defaultHeight: 0.08 }),
    Object.freeze({ type: "multiline", label: _t("Multiline"), defaultWidth: 0.4, defaultHeight: 0.18 }),
    Object.freeze({ type: "checkbox", label: _t("Checkbox"), defaultWidth: 0.08, defaultHeight: 0.08 }),
    Object.freeze({ type: "radio", label: _t("Radio"), defaultWidth: 0.24, defaultHeight: 0.12 }),
    Object.freeze({ type: "selection", label: _t("Selection"), defaultWidth: 0.3, defaultHeight: 0.12 }),
    Object.freeze({ type: "date", label: _t("Date"), defaultWidth: 0.24, defaultHeight: 0.08 }),
    Object.freeze({ type: "strikethrough", label: _t("Strikethrough"), defaultWidth: 0.2, defaultHeight: 0.08 }),
    Object.freeze({ type: "stamp", label: _t("Stamp"), defaultWidth: 0.22, defaultHeight: 0.14 }),
]);
const DEFAULT_PALETTE_ENTRY = PALETTE_ENTRIES.find((entry) => entry.type === "text") || PALETTE_ENTRIES[0];

export const FIELD_PALETTE_TYPES = Object.freeze(PALETTE_ENTRIES.map((entry) => entry.type));

export function getFieldPaletteEntries() {
    return PALETTE_ENTRIES.map((entry) => ({ ...entry }));
}

export function getPaletteEntryByType(type) {
    return PALETTE_ENTRIES.find((entry) => entry.type === type) || DEFAULT_PALETTE_ENTRY;
}
