import { expect, test } from "@odoo/hoot";

import {
    serializeFieldGeometry,
    serializeTemplateFieldsForBackend,
} from "@open_sign_web/js/template_canvas";

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

test("serializeTemplateFieldsForBackend maps to backend-safe keys only", () => {
    const payload = serializeTemplateFieldsForBackend([
        {
            id: 7,
            type: "selection",
            label: "  Approver  ",
            required: true,
            sequence: 30,
            x: 0.2,
            y: 0.3,
            width: 0.4,
            height: 0.1,
            page: 2,
            defaultValue: "A",
            validationRegex: "^[A-Z]$",
            minLength: 1,
            maxLength: 3,
            optionList: " A \n\nB ",
            placeholder: "editor-only",
            helpText: "editor-only",
        },
    ]);

    expect(payload).toEqual([
        {
            type: "selection",
            label: "Approver",
            required: true,
            sequence: 30,
            default_value: "A",
            validation_regex: "^[A-Z]$",
            min_length: null,
            max_length: null,
            option_ids: [
                [0, 0, { value: "A", label: "A", sequence: 10 }],
                [0, 0, { value: "B", label: "B", sequence: 20 }],
            ],
            page: 2,
            x: 0.2,
            y: 0.3,
            width: 0.4,
            height: 0.1,
        },
    ]);
});
