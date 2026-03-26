import { beforeEach, describe, expect, test } from "@odoo/hoot";

import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { startInteraction } from "@web/../tests/public/helpers";
import { rpc } from "@web/core/network/rpc";

import { OpenSignPortalPdfSurface } from "@open_sign_portal/interactions/portal_pdf_surface";
import { OpenSignPortalSession } from "@open_sign_portal/interactions/portal_sign_session";

describe.current.tags("headless", "open_sign_portal");

function makeSessionHtml({ extraContent = "", includeBaseField = true } = {}) {
    return `
        <div
            class="o_open_sign_session"
            data-signer-id="42"
            data-submit-url="/my/sign/42/submit"
            data-decline-url="/my/sign/42/decline"
            data-request-revision="3"
            data-access-token="token-123"
            data-consent-hash="consent-hash-123"
        >
            <div class="o_open_sign_error d-none"></div>
            <div class="o_open_sign_success d-none"></div>
            <div class="o_open_sign_request_status"></div>
            <input class="o_open_sign_consent" type="checkbox" checked />
            <textarea class="o_open_sign_decline_reason">Decline reason</textarea>
            ${
                includeBaseField
                    ? `<div class="o_open_sign_field" data-field-id="10" data-field-type="text" data-editable="true">
                <input class="o_open_sign_input" value="Field value" />
            </div>`
                    : ""
            }
            ${extraContent}
        </div>
    `;
}

function makeSurfaceHtml(
    fields,
    pdfRenderUrl = "/my/sign/42/document?viewer=1&viewer_token=viewer-proof&access_token=token-123"
) {
    return `
        <div class="o_open_sign_pdf_surface" data-pdf-render-url="${pdfRenderUrl}">
            <script type="application/json" class="o_open_sign_fields_payload">${JSON.stringify(fields)}</script>
        </div>
    `;
}

async function startPortalInteraction(options = {}) {
    const { core } = await startInteraction(OpenSignPortalSession, makeSessionHtml(options));
    return core.interactions[0].interaction;
}

beforeEach(() => {
    window.sessionStorage.clear();
});

test("submit keeps pending key on request_locked", async () => {
    const interaction = await startPortalInteraction();
    const key = interaction._getOrCreatePendingIdempotencyKey("submit");
    patchWithCleanup(rpc, {
        _rpc: async () => ({ ok: false, error_code: "request_locked", message: "Locked" }),
    });

    await interaction.onClickSubmit();

    expect(interaction._getPendingIdempotencyKey("submit")).toBe(key);
});

test("decline keeps pending key on request_locked", async () => {
    const interaction = await startPortalInteraction();
    const key = interaction._getOrCreatePendingIdempotencyKey("decline");
    patchWithCleanup(rpc, {
        _rpc: async () => ({ ok: false, error_code: "request_locked", message: "Locked" }),
    });

    await interaction.onClickDecline();

    expect(interaction._getPendingIdempotencyKey("decline")).toBe(key);
});

test("pending key is cleared on success", async () => {
    const interaction = await startPortalInteraction();
    interaction._getOrCreatePendingIdempotencyKey("submit");
    patchWithCleanup(rpc, {
        _rpc: async () => ({ ok: true, request_revision: 4 }),
    });

    await interaction.onClickSubmit();

    expect(interaction._getPendingIdempotencyKey("submit")).toBe(false);
});

test("pending key is cleared on definitive json error", async () => {
    const interaction = await startPortalInteraction();
    interaction._getOrCreatePendingIdempotencyKey("submit");
    patchWithCleanup(rpc, {
        _rpc: async () => ({ ok: false, error_code: "validation_error", message: "Invalid" }),
    });

    await interaction.onClickSubmit();

    expect(interaction._getPendingIdempotencyKey("submit")).toBe(false);
});

test("pending key is preserved on transport failure", async () => {
    const interaction = await startPortalInteraction();
    const key = interaction._getOrCreatePendingIdempotencyKey("submit");
    patchWithCleanup(rpc, {
        _rpc: async () => {
            throw new Error("network failure");
        },
    });

    await interaction.onClickSubmit();

    expect(interaction._getPendingIdempotencyKey("submit")).toBe(key);
});

test("pdf surface renders continuous page stack with overlay fields", async () => {
    patchWithCleanup(OpenSignPortalPdfSurface.prototype, {
        async _loadPages() {
            return [
                { number: 1, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page1" },
                { number: 2, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page2" },
            ];
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 10,
                label: "Full Name",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.2,
                width: 0.3,
                height: 0.08,
                supported_on_portal: true,
                editable: true,
                value: "Field value",
                has_value: true,
                options: [],
            },
        ]),
    });

    expect(interaction.el.querySelectorAll(".o_open_sign_pdf_page_card").length).toBe(2);
    const fieldNode = interaction.el.querySelector('.o_open_sign_pdf_page_overlay .o_open_sign_field[data-field-id="10"]');
    expect(Boolean(fieldNode)).toBe(true);
    expect(fieldNode.dataset.page).toBe("1");
    expect(fieldNode.dataset.editable).toBe("true");
    expect(fieldNode.getAttribute("style").includes("left:10%")).toBe(true);
    expect(fieldNode.getAttribute("style").includes("top:20%")).toBe(true);
});

test("collector skips disabled signature placeholder fields", async () => {
    patchWithCleanup(OpenSignPortalPdfSurface.prototype, {
        async _loadPages() {
            return [{ number: 1, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page1" }];
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 10,
                label: "Full Name",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.1,
                width: 0.3,
                height: 0.08,
                supported_on_portal: true,
                editable: true,
                value: "Field value",
                has_value: true,
                options: [],
            },
            {
                id: 11,
                label: "Signer Signature",
                type: "signature",
                required: true,
                page: 1,
                x: 0.2,
                y: 0.3,
                width: 0.35,
                height: 0.1,
                supported_on_portal: false,
                editable: false,
                value: false,
                has_value: false,
                options: [],
            },
        ]),
    });

    expect(interaction.el.textContent.includes("Signature capture arrives in T320.")).toBe(true);
    expect(interaction._collectValuesPayload()).toEqual([
        { field_id: 10, value: "Field value" },
    ]);
});

test("placeholder copy uses has_value instead of raw signature payload value", async () => {
    patchWithCleanup(OpenSignPortalPdfSurface.prototype, {
        async _loadPages() {
            return [{ number: 1, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page1" }];
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 21,
                label: "Stored Signature",
                type: "signature",
                required: false,
                page: 1,
                x: 0.2,
                y: 0.3,
                width: 0.35,
                height: 0.1,
                supported_on_portal: false,
                editable: false,
                value: false,
                has_value: true,
                options: [],
            },
        ]),
    });

    expect(interaction.el.textContent.includes("Signature on file. Portal capture arrives in T320.")).toBe(true);
});

test("toggle fields use has_value for completion state even when visually unchecked", async () => {
    patchWithCleanup(OpenSignPortalPdfSurface.prototype, {
        async _loadPages() {
            return [{ number: 1, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page1" }];
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 22,
                label: "Unchecked Checkbox",
                type: "checkbox",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.2,
                width: 0.2,
                height: 0.05,
                supported_on_portal: true,
                editable: true,
                value: false,
                has_value: true,
                options: [],
            },
            {
                id: 23,
                label: "Unchecked Strike",
                type: "strikethrough",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.3,
                width: 0.25,
                height: 0.05,
                supported_on_portal: true,
                editable: true,
                value: false,
                has_value: true,
                options: [],
            },
        ]),
    });

    expect(interaction.el.querySelector("#o_open_sign_field_22").classList.contains("o_is_complete")).toBe(true);
    expect(interaction.el.querySelector("#o_open_sign_field_23").classList.contains("o_is_complete")).toBe(true);
    expect(interaction.el.querySelector("#o_open_sign_field_22 .o_open_sign_checkbox").checked).toBe(false);
    expect(interaction.el.querySelector("#o_open_sign_field_23 .o_open_sign_checkbox").checked).toBe(false);
});

test("pdf surface renders readonly text fields as disabled controls", async () => {
    patchWithCleanup(OpenSignPortalPdfSurface.prototype, {
        async _loadPages() {
            return [{ number: 1, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page1" }];
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 12,
                label: "Review Name",
                type: "text",
                required: true,
                page: 1,
                x: 0.15,
                y: 0.15,
                width: 0.3,
                height: 0.08,
                supported_on_portal: true,
                editable: false,
                value: "Read only value",
                has_value: true,
                options: [],
            },
        ]),
    });

    const input = interaction.el.querySelector('#o_open_sign_field_12 .o_open_sign_input');
    expect(Boolean(input)).toBe(true);
    expect(input.disabled).toBe(true);
    expect(interaction.el.querySelector('#o_open_sign_field_12').dataset.editable).toBe("false");
});
