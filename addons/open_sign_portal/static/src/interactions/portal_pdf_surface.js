/** @odoo-module **/

import {
    DEFAULT_PAGE_SIZE,
    formatOverlayFieldStyle,
    formatPdfPageStyle,
    loadPdfPagesFromUrl,
} from "@open_sign_web/js/pdf_surface_utils";

const SINGLE_LINE_FIELD_TYPES = new Set([
    "text",
    "name",
    "company",
    "initials",
    "email",
    "phone",
    "date",
]);
const TEXTAREA_FIELD_TYPES = new Set(["multiline"]);
const TOGGLE_FIELD_TYPES = new Set(["checkbox", "strikethrough"]);
const PLACEHOLDER_FIELD_TYPES = new Set(["signature", "stamp"]);

function escapeAttr(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

function asBool(value) {
    return value === true || value === "true";
}

function isPresentValue(field) {
    if ("has_value" in field) {
        return Boolean(field.has_value);
    }
    if (PLACEHOLDER_FIELD_TYPES.has(field.type)) {
        return Boolean(field.has_value);
    }
    return Boolean(String(field.value || "").trim());
}

function buildFieldClasses(field) {
    const classes = ["o_open_sign_field"];
    if (!field.editable) {
        classes.push("o_is_readonly");
    }
    if (PLACEHOLDER_FIELD_TYPES.has(field.type)) {
        classes.push("o_is_placeholder");
    }
    if (isPresentValue(field)) {
        classes.push("o_is_complete");
    }
    return classes.join(" ");
}

function buildPlaceholderMessage(field) {
    const typeLabel = field.type === "stamp" ? "Stamp" : "Signature";
    return field.has_value
        ? `${typeLabel} on file. Portal capture arrives in T320.`
        : `${typeLabel} capture arrives in T320.`;
}

function buildOptionsMarkup(field) {
    return (Array.isArray(field.options) ? field.options : [])
        .map((option) => {
            const optionValue = option?.value ?? "";
            const optionLabel = escapeHtml(option?.label || optionValue);
            return `<option value="${escapeAttr(optionValue)}"${
                field.value === optionValue ? " selected" : ""
            }>${optionLabel}</option>`;
        })
        .join("");
}

function buildRadioMarkup(field) {
    return (Array.isArray(field.options) ? field.options : [])
        .map((option) => {
            const optionValue = option?.value ?? "";
            const optionLabel = escapeHtml(option?.label || optionValue);
            return `
                <label class="o_open_sign_field_choice">
                    <input
                        class="form-check-input o_open_sign_radio"
                        type="radio"
                        name="open_sign_radio_${field.id}"
                        value="${escapeAttr(optionValue)}"
                        ${field.value === optionValue ? "checked" : ""}
                        ${field.editable ? "" : "disabled"}
                    />
                    <span>${optionLabel}</span>
                </label>
            `;
        })
        .join("");
}

function buildFieldControlMarkup(field) {
    if (SINGLE_LINE_FIELD_TYPES.has(field.type)) {
        const inputType = field.type === "email" ? "email" : field.type === "phone" ? "tel" : field.type === "date" ? "date" : "text";
        return `
            <input
                type="${inputType}"
                class="form-control form-control-sm o_open_sign_input"
                value="${escapeAttr(field.value || "")}"
                ${field.editable ? "" : "disabled"}
            />
        `;
    }
    if (TEXTAREA_FIELD_TYPES.has(field.type)) {
        return `
            <textarea
                class="form-control form-control-sm o_open_sign_input o_open_sign_multiline_input"
                rows="3"
                ${field.editable ? "" : "disabled"}
            >${escapeHtml(field.value || "")}</textarea>
        `;
    }
    if (field.type === "selection") {
        return `
            <select class="form-select form-select-sm o_open_sign_input" ${field.editable ? "" : "disabled"}>
                <option value="">Select...</option>
                ${buildOptionsMarkup(field)}
            </select>
        `;
    }
    if (field.type === "radio") {
        return `<div class="o_open_sign_field_choices">${buildRadioMarkup(field)}</div>`;
    }
    if (TOGGLE_FIELD_TYPES.has(field.type)) {
        const checked = asBool(field.value);
        const label = field.type === "strikethrough" ? "Apply strikethrough" : "Checked";
        return `
            <label class="o_open_sign_field_toggle">
                <input
                    class="form-check-input o_open_sign_checkbox"
                    type="checkbox"
                    ${checked ? "checked" : ""}
                    ${field.editable ? "" : "disabled"}
                />
                <span>${label}</span>
            </label>
        `;
    }
    if (PLACEHOLDER_FIELD_TYPES.has(field.type)) {
        return `<div class="o_open_sign_field_placeholder">${escapeHtml(buildPlaceholderMessage(field))}</div>`;
    }
    return `<div class="o_open_sign_field_placeholder">This field type is not supported on the portal yet.</div>`;
}

function buildFieldMarkup(field) {
    return `
        <div
            id="o_open_sign_field_${field.id}"
            class="${buildFieldClasses(field)}"
            style="${formatOverlayFieldStyle(field)}"
            data-field-id="${field.id}"
            data-field-type="${field.type}"
            data-page="${field.page}"
            data-required="${field.required ? "true" : "false"}"
            data-editable="${field.editable ? "true" : "false"}"
        >
            <div class="o_open_sign_field_label_row">
                <span class="o_open_sign_field_label">${escapeHtml(field.label)}</span>
                ${field.required ? '<span class="o_open_sign_field_required">*</span>' : ""}
            </div>
            <div class="o_open_sign_field_body">
                ${buildFieldControlMarkup(field)}
            </div>
        </div>
    `;
}

function buildPageMarkup(page, fields) {
    return `
        <article class="o_open_sign_pdf_page_card" data-page-number="${page.number}">
            <div class="o_open_sign_pdf_page_meta">
                <span>Page ${page.number}</span>
            </div>
            <div class="o_open_sign_pdf_page_viewport" style="${formatPdfPageStyle(page, DEFAULT_PAGE_SIZE)}">
                <img
                    class="o_open_sign_pdf_page_image"
                    src="${page.imageDataUrl}"
                    alt="PDF page ${page.number}"
                    draggable="false"
                />
                <div class="o_open_sign_pdf_page_overlay">
                    ${fields.map(buildFieldMarkup).join("")}
                </div>
            </div>
        </article>
    `;
}

export class OpenSignPortalPdfSurface {
    constructor(session) {
        this.session = session;
        this.root = session.el.querySelector(".o_open_sign_pdf_surface");
        this.fields = [];
        this.pdfRenderUrl = this.root?.dataset.pdfRenderUrl || "";
        this.pages = [];
        this.loadError = false;
        this._parseFieldPayload();
    }

    _parseFieldPayload() {
        if (!this.root) {
            return;
        }
        const payloadNode = this.root.querySelector(".o_open_sign_fields_payload");
        if (!payloadNode?.textContent?.trim()) {
            return;
        }
        try {
            const payload = JSON.parse(payloadNode.textContent);
            this.fields = Array.isArray(payload) ? payload : [];
        } catch {
            this.fields = [];
        }
    }

    async willStart() {
        if (!this.root) {
            return;
        }
        if (!this.pdfRenderUrl) {
            this.pages = [];
            this.loadError = true;
            return;
        }
        try {
            this.pages = await this._loadPages();
            this.loadError = false;
        } catch {
            this.pages = [];
            this.loadError = true;
        }
    }

    async _loadPages() {
        return loadPdfPagesFromUrl(this.pdfRenderUrl);
    }

    start() {
        if (!this.root) {
            return;
        }
        if (!this.pdfRenderUrl) {
            this._renderUnavailable("PDF preview is unavailable for this signing request.");
            return;
        }
        this._renderLoading();
        if (this.loadError) {
            this._renderUnavailable("Could not load the inline PDF preview. Use View PDF instead.");
            return;
        }
        this._renderPages(this.pages);
    }

    _fieldsForPage(pageNumber) {
        return this.fields.filter((field) => Number(field.page) === Number(pageNumber));
    }

    _renderLoading() {
        this.root.innerHTML = `
            <div class="o_open_sign_pdf_surface_state text-muted">
                Loading inline PDF preview...
            </div>
        `;
    }

    _renderUnavailable(message) {
        this.root.innerHTML = `
            <div class="alert alert-warning mb-0" role="alert">
                ${message}
            </div>
        `;
    }

    _renderPages(pages) {
        if (!Array.isArray(pages) || !pages.length) {
            this._renderUnavailable("PDF preview is unavailable for this signing request.");
            return;
        }
        this.root.innerHTML = `
            <div class="o_open_sign_pdf_pages">
                ${pages.map((page) => buildPageMarkup(page, this._fieldsForPage(page.number))).join("")}
            </div>
        `;
    }
}
