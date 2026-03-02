import { describe, expect, test } from "@odoo/hoot";

import { normalizeCanvasToPdfCoordinates } from "@open_sign_web/js/template_canvas";

describe.current.tags("headless", "open_sign_web");

test("normalizeCanvasToPdfCoordinates scales geometry by canvas/pdf ratios", () => {
    const result = normalizeCanvasToPdfCoordinates(
        { page: 1, x: 50, y: 60, width: 100, height: 40 },
        { width: 500, height: 1000 },
        { width: 1000, height: 2000 }
    );

    expect(result).toEqual({
        page: 1,
        x: 100,
        y: 120,
        width: 200,
        height: 80,
    });
});

test("normalizeCanvasToPdfCoordinates applies safe fallbacks and clamps output", () => {
    const result = normalizeCanvasToPdfCoordinates(
        { page: 2, x: 10, y: -4, width: 50, height: "abc" },
        { width: 0, height: "foo" },
        { width: 0, height: 0 }
    );

    expect(result).toEqual({
        page: 2,
        x: 1,
        y: 0,
        width: 1,
        height: 0,
    });
});
