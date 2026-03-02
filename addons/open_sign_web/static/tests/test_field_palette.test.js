import { describe, expect, test } from "@odoo/hoot";

import {
    FIELD_PALETTE_TYPES,
    getFieldPaletteEntries,
    getPaletteEntryByType,
} from "@open_sign_web/js/field_palette";

describe.current.tags("headless", "open_sign_web");

test("field palette exposes backend-aligned type keys", () => {
    expect(FIELD_PALETTE_TYPES.includes("initials")).toBe(true);
    expect(FIELD_PALETTE_TYPES.includes("multiline")).toBe(true);
    expect(FIELD_PALETTE_TYPES.includes("selection")).toBe(true);
});

test("getFieldPaletteEntries returns entries with defaults", () => {
    const entries = getFieldPaletteEntries();
    const signature = entries.find((entry) => entry.type === "signature");
    expect(Boolean(signature)).toBe(true);
    expect(signature.defaultWidth > 0).toBe(true);
    expect(signature.defaultHeight > 0).toBe(true);
});

test("getPaletteEntryByType falls back to a known type", () => {
    const fallback = getPaletteEntryByType("non_existing");
    expect(Boolean(fallback)).toBe(true);
    expect(fallback.type).toBe("text");
});
