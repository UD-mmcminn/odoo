import { expect, test } from "@odoo/hoot";

import { normalizeCanvasToPdfCoordinates } from "@open_sign_web/js/template_canvas";

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
