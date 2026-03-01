import { expect, test } from "@odoo/hoot";

import { serializeFieldGeometry } from "@open_sign_web/js/template_canvas";

test("serializeFieldGeometry normalizes negative and invalid values", () => {
    const geometry = serializeFieldGeometry({
        page: 0,
        x: -10,
        y: "12.5",
        width: "abc",
        height: 20,
    });

    expect(geometry).toEqual({
        page: 1,
        x: 0,
        y: 12.5,
        width: 0,
        height: 20,
    });
});
