import { beforeEach, describe, expect, test } from "@odoo/hoot";

import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { startInteraction } from "@web/../tests/public/helpers";
import { rpc } from "@web/core/network/rpc";

import { OpenSignPortalPdfSurface } from "@open_sign_portal/interactions/portal_pdf_surface";
import { OpenSignPortalSession } from "@open_sign_portal/interactions/portal_sign_session";

describe.current.tags("headless", "open_sign_portal");

const VALID_SIGNATURE_DATA_URL =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4//8/AwAI/AL+X2VINwAAAABJRU5ErkJggg==";

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

function makeFieldSummaryMarkup(fields) {
    return `
        <div class="o_open_sign_field_summary">
            ${fields.map((field) => `
                <button
                    type="button"
                    class="o_open_sign_field_summary_item"
                    data-field-id="${field.id}"
                    data-page="${field.page}"
                    data-required="${field.required ? "true" : "false"}"
                    data-editable="${field.editable ? "true" : "false"}"
                >
                    ${field.label}
                </button>
            `).join("")}
        </div>
    `;
}

function makeSurfaceHtml(
    fields,
    pdfRenderUrl = "/my/sign/42/document?viewer=1&viewer_token=viewer-proof&access_token=token-123"
) {
    const hasActionableFields = fields.some(
        (field) => field.editable && field.supported_on_portal
    );
    return `
        <div class="o_open_sign_surface_actions">
            ${hasActionableFields ? '<button type="button" class="o_open_sign_next_field">Next field</button>' : ""}
        </div>
        <div class="o_open_sign_pdf_surface" data-pdf-render-url="${pdfRenderUrl}">
            <script type="application/json" class="o_open_sign_fields_payload">${JSON.stringify(fields)}</script>
        </div>
        ${makeFieldSummaryMarkup(fields)}
    `;
}

function makeCapturePayload(overrides = {}) {
    return {
        method: "draw",
        display_name: "Alice Signer",
        signed_payload_attachment_id: 81,
        signature_image_mime_type: "image/png",
        signature_image_byte_size: 70,
        preview_data_url: VALID_SIGNATURE_DATA_URL,
        ...overrides,
    };
}

async function startPortalInteraction(options = {}) {
    const { core } = await startInteraction(OpenSignPortalSession, makeSessionHtml(options));
    return core.interactions[0].interaction;
}

function mockPdfPages(
    pages = [{ number: 1, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page1" }]
) {
    patchWithCleanup(OpenSignPortalPdfSurface.prototype, {
        async _loadPages() {
            return pages;
        },
    });
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
    mockPdfPages([
        { number: 1, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page1" },
        { number: 2, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page2" },
    ]);
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

test("clicking a signature field opens the capture dialog", async () => {
    mockPdfPages();
    let openedFieldId = false;
    patchWithCleanup(OpenSignPortalPdfSurface.prototype, {
        _openCaptureDialog(field) {
            openedFieldId = field.id;
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
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
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: false,
                has_value: false,
                preview_url: false,
                options: [],
            },
        ]),
    });

    interaction.el.querySelector("#o_open_sign_field_11").click();

    expect(openedFieldId).toBe(11);
});

test("successful signature adopt updates preview, marks complete, and auto-advances", async () => {
    mockPdfPages();
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 21,
                label: "Signer Signature",
                type: "signature",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.2,
                width: 0.35,
                height: 0.1,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: false,
                has_value: false,
                preview_url: false,
                options: [],
            },
            {
                id: 22,
                label: "Next Missing Field",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.4,
                width: 0.3,
                height: 0.08,
                sequence: 20,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    interaction.pdfSurface._applyCapturePayload(21, makeCapturePayload());

    expect(interaction.el.querySelector("#o_open_sign_field_21").classList.contains("o_is_complete")).toBe(true);
    expect(
        interaction.el.querySelector("#o_open_sign_field_21 .o_open_sign_capture_preview").getAttribute("src")
    ).toBe(VALID_SIGNATURE_DATA_URL);
    expect(interaction.el.querySelector("#o_open_sign_field_22").classList.contains("o_is_active")).toBe(true);
});

test("toggle fields use has_value for completion state even when visually unchecked", async () => {
    mockPdfPages();
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
    mockPdfPages();
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

test("initial active field is the first incomplete actionable field", async () => {
    mockPdfPages([
        { number: 1, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page1" },
        { number: 2, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page2" },
    ]);
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 31,
                label: "Completed Name",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.15,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "Alice",
                has_value: true,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
            {
                id: 32,
                label: "First Missing Field",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.3,
                width: 0.3,
                height: 0.08,
                sequence: 20,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
            {
                id: 33,
                label: "Second Missing Field",
                type: "text",
                required: false,
                page: 2,
                x: 0.1,
                y: 0.2,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    expect(interaction.el.querySelector("#o_open_sign_field_32").classList.contains("o_is_active")).toBe(true);
    expect(interaction.el.querySelector('.o_open_sign_field_summary_item[data-field-id="32"]').classList.contains("o_is_active")).toBe(true);
    expect(document.activeElement).not.toBe(interaction.el.querySelector("#o_open_sign_field_32 .o_open_sign_input"));
});

test("next field moves to the next incomplete field and disables when all are complete", async () => {
    mockPdfPages();
    const scrollCalls = [];
    patchWithCleanup(HTMLElement.prototype, {
        scrollIntoView() {
            scrollCalls.push(this.dataset.fieldId || this.dataset.pageNumber || "unknown");
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 41,
                label: "First Missing Field",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.15,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
            {
                id: 42,
                label: "Second Missing Field",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.3,
                width: 0.3,
                height: 0.08,
                sequence: 20,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    interaction.el.querySelector(".o_open_sign_next_field").click();
    expect(interaction.el.querySelector("#o_open_sign_field_42").classList.contains("o_is_active")).toBe(true);
    expect(scrollCalls.includes("42")).toBe(true);

    const firstInput = interaction.el.querySelector("#o_open_sign_field_41 .o_open_sign_input");
    const secondInput = interaction.el.querySelector("#o_open_sign_field_42 .o_open_sign_input");
    firstInput.value = "Alice";
    firstInput.dispatchEvent(new Event("input", { bubbles: true }));
    secondInput.value = "Signed";
    secondInput.dispatchEvent(new Event("input", { bubbles: true }));

    expect(interaction.el.querySelector(".o_open_sign_next_field").disabled).toBe(true);
});

test("next field respects the current cursor when the active field is already complete", async () => {
    mockPdfPages();
    const scrollCalls = [];
    patchWithCleanup(HTMLElement.prototype, {
        scrollIntoView() {
            scrollCalls.push(this.dataset.fieldId || this.dataset.pageNumber || "unknown");
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 45,
                label: "Earlier Missing Field",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.15,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
            {
                id: 46,
                label: "Current Complete Field",
                type: "text",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.3,
                width: 0.3,
                height: 0.08,
                sequence: 20,
                supported_on_portal: true,
                editable: true,
                value: "Done",
                has_value: true,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
            {
                id: 47,
                label: "Later Missing Field",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.45,
                width: 0.3,
                height: 0.08,
                sequence: 30,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    interaction.el.querySelector("#o_open_sign_field_46").click();
    expect(interaction.el.querySelector("#o_open_sign_field_46").classList.contains("o_is_active")).toBe(true);

    interaction.el.querySelector(".o_open_sign_next_field").click();
    expect(interaction.el.querySelector("#o_open_sign_field_47").classList.contains("o_is_active")).toBe(true);
    expect(interaction.el.querySelector("#o_open_sign_field_45").classList.contains("o_is_active")).toBe(false);
    expect(scrollCalls.includes("47")).toBe(true);
});

test("next field wraps circularly after the current cursor", async () => {
    mockPdfPages();
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 48,
                label: "Wrapped Missing Field",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.15,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
            {
                id: 49,
                label: "Middle Complete Field",
                type: "text",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.3,
                width: 0.3,
                height: 0.08,
                sequence: 20,
                supported_on_portal: true,
                editable: true,
                value: "Complete",
                has_value: true,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
            {
                id: 50,
                label: "Last Complete Field",
                type: "text",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.45,
                width: 0.3,
                height: 0.08,
                sequence: 30,
                supported_on_portal: true,
                editable: true,
                value: "Also complete",
                has_value: true,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    interaction.el.querySelector("#o_open_sign_field_50").click();
    interaction.el.querySelector(".o_open_sign_next_field").click();

    expect(interaction.el.querySelector("#o_open_sign_field_48").classList.contains("o_is_active")).toBe(true);
});

test("tab and shift-tab move across actionable fields without wrapping", async () => {
    mockPdfPages([
        { number: 1, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page1" },
        { number: 2, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page2" },
    ]);
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 51,
                label: "Page One Field",
                type: "text",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.15,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
            {
                id: 52,
                label: "Page Two Field",
                type: "text",
                required: false,
                page: 2,
                x: 0.1,
                y: 0.2,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    const firstInput = interaction.el.querySelector("#o_open_sign_field_51 .o_open_sign_input");
    const secondInput = interaction.el.querySelector("#o_open_sign_field_52 .o_open_sign_input");
    firstInput.focus();
    const forwardEvent = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    firstInput.dispatchEvent(forwardEvent);
    expect(forwardEvent.defaultPrevented).toBe(true);
    expect(interaction.el.querySelector("#o_open_sign_field_52").classList.contains("o_is_active")).toBe(true);
    expect(document.activeElement).toBe(secondInput);

    const noWrapEvent = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    secondInput.dispatchEvent(noWrapEvent);
    expect(noWrapEvent.defaultPrevented).toBe(false);

    const backwardEvent = new KeyboardEvent("keydown", {
        key: "Tab",
        shiftKey: true,
        bubbles: true,
        cancelable: true,
    });
    secondInput.dispatchEvent(backwardEvent);
    expect(backwardEvent.defaultPrevented).toBe(true);
    expect(interaction.el.querySelector("#o_open_sign_field_51").classList.contains("o_is_active")).toBe(true);
    expect(document.activeElement).toBe(firstInput);
});

test("next field and tab traversal include signature trigger fields", async () => {
    mockPdfPages();
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 53,
                label: "Signature Step",
                type: "signature",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.15,
                width: 0.35,
                height: 0.1,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: false,
                has_value: false,
                preview_url: false,
                options: [],
            },
            {
                id: 54,
                label: "Following Text Field",
                type: "text",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.35,
                width: 0.3,
                height: 0.08,
                sequence: 20,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    expect(interaction.el.querySelector("#o_open_sign_field_53").classList.contains("o_is_active")).toBe(true);
    expect(document.activeElement).not.toBe(interaction.el.querySelector("#o_open_sign_field_53 .o_open_sign_capture_button"));

    interaction.el.querySelector(".o_open_sign_next_field").click();
    expect(interaction.el.querySelector("#o_open_sign_field_54").classList.contains("o_is_active")).toBe(true);

    const textInput = interaction.el.querySelector("#o_open_sign_field_54 .o_open_sign_input");
    textInput.focus();
    const backwardEvent = new KeyboardEvent("keydown", {
        key: "Tab",
        shiftKey: true,
        bubbles: true,
        cancelable: true,
    });
    textInput.dispatchEvent(backwardEvent);
    expect(backwardEvent.defaultPrevented).toBe(true);
    expect(interaction.el.querySelector("#o_open_sign_field_53").classList.contains("o_is_active")).toBe(true);
    expect(document.activeElement).toBe(interaction.el.querySelector("#o_open_sign_field_53 .o_open_sign_capture_button"));
});

test("summary click scrolls to and activates the linked field", async () => {
    mockPdfPages();
    const scrollCalls = [];
    patchWithCleanup(HTMLElement.prototype, {
        scrollIntoView() {
            scrollCalls.push(this.dataset.fieldId || this.dataset.pageNumber || "unknown");
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 61,
                label: "First Summary Field",
                type: "text",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.15,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
            {
                id: 62,
                label: "Second Summary Field",
                type: "text",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.3,
                width: 0.3,
                height: 0.08,
                sequence: 20,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    interaction.el.querySelector('.o_open_sign_field_summary_item[data-field-id="62"]').click();
    expect(interaction.el.querySelector("#o_open_sign_field_62").classList.contains("o_is_active")).toBe(true);
    expect(scrollCalls.includes("62")).toBe(true);
    expect(document.activeElement).toBe(interaction.el.querySelector("#o_open_sign_field_62 .o_open_sign_input"));
});

test("save allows blank required fields without client blocking", async () => {
    mockPdfPages();
    let rpcCalls = 0;
    patchWithCleanup(rpc, {
        _rpc: async () => {
            rpcCalls += 1;
            return { ok: true, request_revision: 4 };
        },
    });

    const blankRequiredInteraction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 71,
                label: "Required Text",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.2,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    await blankRequiredInteraction.onClickSave();
    expect(rpcCalls).toBe(1);
    expect(blankRequiredInteraction.el.querySelector("#o_open_sign_field_71").classList.contains("o_is_invalid")).toBe(false);
});

test("collector includes signature payloads under value and recapture replaces the local payload", async () => {
    mockPdfPages();
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 73,
                label: "Signature Value",
                type: "signature",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.2,
                width: 0.35,
                height: 0.1,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: false,
                has_value: false,
                preview_url: false,
                options: [],
            },
        ]),
    });

    interaction.pdfSurface._applyCapturePayload(73, makeCapturePayload());
    expect(interaction._collectValuesPayload()).toEqual([
        {
            field_id: 73,
            value: {
                method: "draw",
                display_name: "Alice Signer",
                signature_image_mime_type: "image/png",
                signature_image_byte_size: 70,
                signed_payload_attachment_id: 81,
            },
        },
    ]);

    interaction.pdfSurface._applyCapturePayload(
        73,
        makeCapturePayload({
            method: "upload",
            display_name: "Alice Replacement",
            signed_payload_attachment_id: 82,
        })
    );
    expect(interaction._collectValuesPayload()).toEqual([
        {
            field_id: 73,
            value: {
                method: "upload",
                display_name: "Alice Replacement",
                signature_image_mime_type: "image/png",
                signature_image_byte_size: 70,
                signed_payload_attachment_id: 82,
            },
        },
    ]);
});

test("save blocks invalid format before rpc", async () => {
    mockPdfPages();
    let rpcCalls = 0;
    patchWithCleanup(rpc, {
        _rpc: async () => {
            rpcCalls += 1;
            return { ok: true, request_revision: 4 };
        },
    });

    const invalidEmailInteraction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 72,
                label: "Invalid Email",
                type: "email",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.2,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "not-an-email",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    invalidEmailInteraction.el.querySelector("#o_open_sign_field_72 .o_open_sign_input").value = "not-an-email";
    await invalidEmailInteraction.onClickSave();
    expect(rpcCalls).toBe(0);
    expect(invalidEmailInteraction.el.querySelector("#o_open_sign_field_72").classList.contains("o_is_invalid")).toBe(true);
    expect(invalidEmailInteraction.el.querySelector(".o_open_sign_error").textContent.includes("Invalid Email")).toBe(true);
    expect(document.activeElement).toBe(invalidEmailInteraction.el.querySelector("#o_open_sign_field_72 .o_open_sign_input"));
});

test("submit focuses and marks the first invalid field before rpc", async () => {
    mockPdfPages([
        { number: 1, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page1" },
        { number: 2, width: 800, height: 1000, imageDataUrl: "data:image/png;base64,page2" },
    ]);
    let rpcCalls = 0;
    patchWithCleanup(rpc, {
        _rpc: async () => {
            rpcCalls += 1;
            return { ok: true, request_revision: 4 };
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 81,
                label: "Required Name",
                type: "text",
                required: true,
                page: 1,
                x: 0.1,
                y: 0.15,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
            {
                id: 82,
                label: "Broken Email",
                type: "email",
                required: false,
                page: 2,
                x: 0.1,
                y: 0.25,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "broken-email",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    interaction.el.querySelector("#o_open_sign_field_82 .o_open_sign_input").value = "broken-email";
    await interaction.onClickSubmit();

    expect(rpcCalls).toBe(0);
    expect(interaction.el.querySelector("#o_open_sign_field_81").classList.contains("o_is_invalid")).toBe(true);
    expect(interaction.el.querySelector("#o_open_sign_field_82").classList.contains("o_is_invalid")).toBe(true);
    expect(interaction.el.querySelector("#o_open_sign_field_81").classList.contains("o_is_active")).toBe(true);
    expect(interaction.el.querySelector(".o_open_sign_error").textContent.includes("Required Name")).toBe(true);
    expect(document.activeElement).toBe(interaction.el.querySelector("#o_open_sign_field_81 .o_open_sign_input"));
});

test("readonly surface disables guided editing but keeps summary jump targeting", async () => {
    mockPdfPages();
    const scrollCalls = [];
    patchWithCleanup(HTMLElement.prototype, {
        scrollIntoView() {
            scrollCalls.push(this.dataset.fieldId || this.dataset.pageNumber || "unknown");
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 91,
                label: "Readonly Field",
                type: "text",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.2,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: false,
                value: "Read only value",
                has_value: true,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    expect(Boolean(interaction.el.querySelector(".o_open_sign_next_field"))).toBe(false);
    expect(Boolean(interaction.el.querySelector(".o_open_sign_field.o_is_active"))).toBe(false);

    interaction.el.querySelector('.o_open_sign_field_summary_item[data-field-id="91"]').click();
    expect(interaction.el.querySelector("#o_open_sign_field_91").classList.contains("o_is_active")).toBe(true);
    expect(scrollCalls.includes("91")).toBe(true);
    expect(document.activeElement).not.toBe(interaction.el.querySelector("#o_open_sign_field_91 .o_open_sign_input"));
});

test("readonly signature fields do not open capture", async () => {
    mockPdfPages();
    let openCount = 0;
    patchWithCleanup(OpenSignPortalPdfSurface.prototype, {
        _openCaptureDialog() {
            openCount += 1;
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 92,
                label: "Readonly Signature",
                type: "signature",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.2,
                width: 0.35,
                height: 0.1,
                sequence: 10,
                supported_on_portal: true,
                editable: false,
                value: {
                    method: "draw",
                    display_name: "Alice",
                    signature_image_mime_type: "image/png",
                    signature_image_byte_size: 70,
                    signed_payload_attachment_id: 91,
                },
                has_value: true,
                preview_url: "/my/sign/42/field/92/payload",
                options: [],
            },
        ]),
    });

    interaction.el.querySelector("#o_open_sign_field_92").click();
    expect(openCount).toBe(0);
    expect(interaction.el.querySelector("#o_open_sign_field_92 .o_open_sign_capture_button").disabled).toBe(true);
});

test("missing pdf render url disables guided navigation affordances", async () => {
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 101,
                label: "PDF Missing Field",
                type: "text",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.2,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ], ""),
    });

    expect(interaction.el.textContent.includes("PDF preview is unavailable for this signing request.")).toBe(true);
    expect(interaction.el.querySelector(".o_open_sign_next_field").disabled).toBe(true);
    expect(interaction.el.querySelector('.o_open_sign_field_summary_item[data-field-id="101"]').disabled).toBe(true);
    expect(Boolean(interaction.el.querySelector(".o_open_sign_field.o_is_active"))).toBe(false);
});

test("pdf load failure disables guided navigation affordances", async () => {
    patchWithCleanup(OpenSignPortalPdfSurface.prototype, {
        async _loadPages() {
            throw new Error("pdf load failure");
        },
    });
    const interaction = await startPortalInteraction({
        includeBaseField: false,
        extraContent: makeSurfaceHtml([
            {
                id: 102,
                label: "PDF Failure Field",
                type: "text",
                required: false,
                page: 1,
                x: 0.1,
                y: 0.2,
                width: 0.3,
                height: 0.08,
                sequence: 10,
                supported_on_portal: true,
                editable: true,
                value: "",
                has_value: false,
                min_length: false,
                max_length: false,
                validation_regex: false,
                options: [],
            },
        ]),
    });

    expect(interaction.el.textContent.includes("Could not load the inline PDF preview. Use View PDF instead.")).toBe(true);
    expect(interaction.el.querySelector(".o_open_sign_next_field").disabled).toBe(true);
    expect(interaction.el.querySelector('.o_open_sign_field_summary_item[data-field-id="102"]').disabled).toBe(true);
    expect(Boolean(interaction.el.querySelector(".o_open_sign_field.o_is_active"))).toBe(false);
});
