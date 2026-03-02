import { describe, expect, test } from "@odoo/hoot";

import {
    applyMoveDelta,
    applyResizeDelta,
    countInvalidFieldRoles,
    isFieldRoleValid,
    serializeFieldGeometry,
    serializeTemplateFieldsForBackend,
    supportsSignatureAdoption,
} from "@open_sign_web/js/template_canvas";

describe.current.tags("headless", "open_sign_web");

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
            roleId: 12,
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
            signatureAdoptionPayload: {
                method: "draw",
                signed_payload_attachment_id: 42,
            },
        },
    ]);

    expect(payload).toEqual([
        {
            role_id: 12,
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

test("isFieldRoleValid accepts only assigned roles from selected template", () => {
    const roles = [{ id: 11, name: "Signer A" }, { id: 12, name: "Signer B" }];

    expect(isFieldRoleValid({ roleId: 11 }, roles)).toBe(true);
    expect(isFieldRoleValid({ roleId: "12" }, roles)).toBe(true);
    expect(isFieldRoleValid({ roleId: 99 }, roles)).toBe(false);
    expect(isFieldRoleValid({ roleId: null }, roles)).toBe(false);
});

test("countInvalidFieldRoles reports missing and stale role assignments", () => {
    const roles = [{ id: 21, name: "Employee" }, { id: 22, name: "Customer" }];
    const fields = [
        { id: 1, roleId: 21 },
        { id: 2, roleId: "22" },
        { id: 3, roleId: 23 },
        { id: 4, roleId: null },
    ];

    expect(countInvalidFieldRoles(fields, roles)).toBe(2);
});

test("serializeTemplateFieldsForBackend can enforce valid role assignment", () => {
    let thrownError = null;
    try {
        serializeTemplateFieldsForBackend(
            [{ label: "Field", roleId: null }],
            {
                requireValidRoles: true,
                availableRoleIds: [{ id: 31 }],
            }
        );
    } catch (error) {
        thrownError = error;
    }

    expect(Boolean(thrownError)).toBe(true);
});

test("supportsSignatureAdoption recognizes signature payload field types", () => {
    expect(supportsSignatureAdoption("signature")).toBe(true);
    expect(supportsSignatureAdoption("stamp")).toBe(true);
    expect(supportsSignatureAdoption("text")).toBe(false);
});

test("applyMoveDelta keeps geometry inside page bounds", () => {
    const movedDownRight = applyMoveDelta(
        { page: 1, x: 0.95, y: 0.95, width: 0.1, height: 0.1 },
        0.25,
        0.3
    );
    expect(movedDownRight).toEqual({
        page: 1,
        x: 0.9,
        y: 0.9,
        width: 0.1,
        height: 0.1,
    });

    const movedUpLeft = applyMoveDelta(
        { page: 1, x: 0.1, y: 0.1, width: 0.2, height: 0.2 },
        -0.5,
        -0.2
    );
    expect(movedUpLeft).toEqual({
        page: 1,
        x: 0,
        y: 0,
        width: 0.2,
        height: 0.2,
    });
});

test("applyResizeDelta enforces minimum field size and edge limits", () => {
    const resizedAtEdge = applyResizeDelta(
        { page: 1, x: 0.98, y: 0.98, width: 0.01, height: 0.01 },
        0.5,
        0.5
    );
    expect(resizedAtEdge).toEqual({
        page: 1,
        x: 0.98,
        y: 0.98,
        width: 0.02,
        height: 0.02,
    });

    const resizedBelowMin = applyResizeDelta(
        { page: 1, x: 0.1, y: 0.2, width: 0.3, height: 0.3 },
        -0.9,
        -0.9
    );
    expect(resizedBelowMin).toEqual({
        page: 1,
        x: 0.1,
        y: 0.2,
        width: 0.02,
        height: 0.02,
    });
});
