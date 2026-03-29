/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { normalizeClientFieldValue } from "@open_sign_web/js/signing_form";
import { openSignatureAdoptionDialog } from "@open_sign_web/js/signature_adoption_dialog";
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
const CAPTURE_FIELD_TYPES = new Set(["signature", "stamp"]);
const CONTROL_SELECTOR = "input, select, textarea, button.o_open_sign_capture_button";

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

function isDirectControlTarget(target) {
    return Boolean(target?.closest?.("input, select, textarea, button, label"));
}

function buildFieldClasses(field) {
    const classes = ["o_open_sign_field"];
    if (!field.editable) {
        classes.push("o_is_readonly");
    }
    if (CAPTURE_FIELD_TYPES.has(field.type)) {
        classes.push("o_is_capture");
    }
    if (field.has_value) {
        classes.push("o_is_complete");
    } else {
        classes.push("o_is_incomplete");
    }
    return classes.join(" ");
}

function buildCapturePrompt(field) {
    const typeLabel = field.type === "stamp" ? "Stamp" : "Signature";
    return field.has_value
        ? `Recapture ${typeLabel}`
        : `Add ${typeLabel}`;
}

function getCapturePreviewSrc(field) {
    return field.preview_data_url || field.preview_url || "";
}

function buildCaptureMarkup(field) {
    const previewSrc = getCapturePreviewSrc(field);
    const typeLabel = field.type === "stamp" ? "Stamp" : "Signature";
    const prompt = buildCapturePrompt(field);
    const hint = field.has_value
        ? `${typeLabel} is ready for save or submit.`
        : `Draw, type, or upload your ${typeLabel.toLowerCase()}.`;
    return `
        <div class="o_open_sign_capture_shell">
            <button
                type="button"
                class="btn btn-light btn-sm o_open_sign_capture_button"
                ${field.editable ? "" : "disabled"}
                aria-label="${escapeAttr(prompt)}"
            >
                ${previewSrc
                    ? `<img class="o_open_sign_capture_preview" src="${escapeAttr(previewSrc)}" alt="${escapeAttr(typeLabel)} preview" />`
                    : `<span class="o_open_sign_capture_empty">${escapeHtml(typeLabel)}</span>`
                }
                <span class="o_open_sign_capture_copy">
                    <span class="o_open_sign_capture_prompt">${escapeHtml(prompt)}</span>
                    <span class="o_open_sign_capture_hint">${escapeHtml(hint)}</span>
                </span>
            </button>
        </div>
    `;
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
        const inputType = field.type === "email"
            ? "email"
            : field.type === "phone"
                ? "tel"
                : field.type === "date"
                    ? "date"
                    : "text";
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
    if (CAPTURE_FIELD_TYPES.has(field.type)) {
        return buildCaptureMarkup(field);
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
        this.summaryRoot = session.el.querySelector(".o_open_sign_field_summary");
        this.nextFieldButton = session.el.querySelector(".o_open_sign_next_field");
        this.fields = [];
        this.fieldById = new Map();
        this.pdfRenderUrl = this.root?.dataset.pdfRenderUrl || "";
        this.pages = [];
        this.loadError = false;
        this.activeFieldId = false;
        this.invalidFieldIds = new Set();
        this.touchedFieldIds = new Set();
        this.surfaceInteractive = false;
        this._interactionsBound = false;
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
        this.fields.sort((left, right) => {
            return (
                Number(left.page) - Number(right.page)
                || Number(left.sequence || 0) - Number(right.sequence || 0)
                || Number(left.id) - Number(right.id)
            );
        });
        this.fieldById = new Map(this.fields.map((field) => [Number(field.id), field]));
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
        this.surfaceInteractive = false;
        if (!this.pdfRenderUrl) {
            this._renderUnavailable("PDF preview is unavailable for this signing request.");
            this._syncAllFieldStates();
            return;
        }
        this._renderLoading();
        if (this.loadError) {
            this._renderUnavailable("Could not load the inline PDF preview. Use View PDF instead.");
            this._syncAllFieldStates();
            return;
        }
        this._renderPages(this.pages);
        this._bindInteractions();
        this.surfaceInteractive = true;
        this._syncAllFieldStates();
        this._initializeActiveField();
        this._updateNextFieldButtonState();
    }

    _bindInteractions() {
        if (this._interactionsBound || !this.root) {
            return;
        }
        this.root.addEventListener("click", (event) => this._onFieldClick(event));
        this.root.addEventListener("input", (event) => this._onFieldInput(event));
        this.root.addEventListener("change", (event) => this._onFieldInput(event));
        this.root.addEventListener("keydown", (event) => this._onFieldKeydown(event));
        this.summaryRoot?.addEventListener("click", (event) => this._onSummaryClick(event));
        this.nextFieldButton?.addEventListener("click", (event) => this._onNextFieldClick(event));
        this._interactionsBound = true;
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

    _getField(fieldId) {
        return this.fieldById.get(Number(fieldId)) || false;
    }

    _getFieldNode(fieldId) {
        return this.root?.querySelector(`.o_open_sign_field[data-field-id="${fieldId}"]`) || false;
    }

    _getSummaryNode(fieldId) {
        return this.summaryRoot?.querySelector(`.o_open_sign_field_summary_item[data-field-id="${fieldId}"]`) || false;
    }

    _getFieldControls(fieldId) {
        const fieldNode = this._getFieldNode(fieldId);
        return fieldNode ? Array.from(fieldNode.querySelectorAll(CONTROL_SELECTOR)) : [];
    }

    _getPrimaryControl(fieldId) {
        const controls = this._getFieldControls(fieldId);
        if (!controls.length) {
            return false;
        }
        const field = this._getField(fieldId);
        if (field?.type === "radio") {
            return controls.find((control) => control.checked) || controls[0];
        }
        return controls[0];
    }

    _isActionableField(field) {
        return Boolean(
            field
            && field.editable
            && field.supported_on_portal
        );
    }

    _getActionableFields() {
        return this.fields.filter((field) => this._isActionableField(field));
    }

    _getOrderedActionableFields() {
        return this._getActionableFields();
    }

    _isEditableSession() {
        return this._getActionableFields().length > 0;
    }

    _normalizeFieldForValidation(field, { enforceRequired }) {
        return {
            type: field.type,
            required: enforceRequired ? Boolean(field.required) : false,
            options: field.options,
            min_length: field.min_length,
            max_length: field.max_length,
            validation_regex: field.validation_regex,
        };
    }

    _getFieldRawValue(fieldId) {
        const fieldNode = this._getFieldNode(fieldId);
        return fieldNode ? this.session._collectValueForField(fieldNode) : false;
    }

    getFieldValuePayload(fieldId) {
        const field = this._getField(fieldId);
        return field?.value || false;
    }

    _validateField(field, { enforceRequired }) {
        return normalizeClientFieldValue(
            this._normalizeFieldForValidation(field, { enforceRequired }),
            this._getFieldRawValue(field.id)
        );
    }

    _hasNormalizedClientValue(field, result) {
        if (!result?.valid) {
            return false;
        }
        if (TOGGLE_FIELD_TYPES.has(field.type)) {
            return Boolean(field.has_value || this.touchedFieldIds.has(field.id));
        }
        if (typeof result.normalizedValueText === "string") {
            return Boolean(result.normalizedValueText.trim());
        }
        if (result.normalizedValueText !== false && result.normalizedValueText !== null && result.normalizedValueText !== undefined) {
            return true;
        }
        if (result.normalizedValueJson && typeof result.normalizedValueJson === "object") {
            return Boolean(Object.keys(result.normalizedValueJson).length);
        }
        return result.normalizedValueJson !== false
            && result.normalizedValueJson !== null
            && result.normalizedValueJson !== undefined;
    }

    _isFieldComplete(field) {
        const validation = this._validateField(field, { enforceRequired: false });
        if (TOGGLE_FIELD_TYPES.has(field.type)) {
            return Boolean(field.has_value || this.touchedFieldIds.has(field.id));
        }
        if (this._hasNormalizedClientValue(field, validation)) {
            return true;
        }
        if (this.touchedFieldIds.has(field.id)) {
            return false;
        }
        return Boolean(field.has_value);
    }

    _formatValidationError(field, errorCode) {
        const errorMessages = {
            required_value_missing: "This field is required.",
            invalid_email: "Enter a valid email address.",
            email_too_long: "Email must be 254 characters or fewer.",
            invalid_phone: "Enter a valid phone number.",
            invalid_initials_length: "Initials must be between 1 and 8 characters.",
            value_not_in_option_set: "Choose one of the available options.",
            invalid_date_iso_format: "Enter a valid date in YYYY-MM-DD format.",
            invalid_date_payload: "Enter a valid date in YYYY-MM-DD format.",
            invalid_strikethrough_payload: "This field value is invalid.",
            invalid_checkbox_payload: "This field value is invalid.",
            control_chars_not_allowed: "Control characters are not allowed.",
            single_line_newline_not_allowed: "This field must stay on one line.",
            value_too_short: "Value is shorter than the allowed minimum.",
            value_too_long: "Value is longer than the allowed maximum.",
            invalid_validation_pattern: "This field has an invalid validation rule.",
            value_does_not_match_pattern: "Value does not match the required format.",
            invalid_signature_payload: "This field value is invalid.",
            signed_payload_attachment_required: "This field value is invalid.",
        };
        return `Fix ${field.label}: ${errorMessages[errorCode] || "This field is invalid."}`;
    }

    _syncFieldState(fieldId) {
        const field = this._getField(fieldId);
        if (!field) {
            return;
        }
        const complete = this._isFieldComplete(field);
        const fieldNode = this._getFieldNode(fieldId);
        const summaryNode = this._getSummaryNode(fieldId);
        for (const node of [fieldNode, summaryNode]) {
            if (!node) {
                continue;
            }
            node.classList.toggle("o_is_complete", complete);
            node.classList.toggle("o_is_incomplete", !complete);
            node.classList.toggle("o_is_active", this.activeFieldId === field.id);
            node.classList.toggle("o_is_invalid", this.invalidFieldIds.has(field.id));
        }
        const controls = this._getFieldControls(fieldId);
        for (const control of controls) {
            if (this.invalidFieldIds.has(field.id)) {
                control.setAttribute("aria-invalid", "true");
            } else {
                control.removeAttribute("aria-invalid");
            }
        }
    }

    _renderFieldBody(fieldId) {
        const field = this._getField(fieldId);
        const fieldNode = this._getFieldNode(fieldId);
        const bodyNode = fieldNode?.querySelector(".o_open_sign_field_body");
        if (!field || !bodyNode) {
            return;
        }
        bodyNode.innerHTML = buildFieldControlMarkup(field);
    }

    _syncAllFieldStates() {
        for (const field of this.fields) {
            this._syncFieldState(field.id);
        }
        this._updateSummaryAvailability();
        this._updateNextFieldButtonState();
    }

    _initializeActiveField() {
        if (!this._isEditableSession()) {
            this.activeFieldId = false;
            this._syncAllFieldStates();
            return;
        }
        const firstIncomplete = this._findFirstIncompleteActionableField();
        if (firstIncomplete) {
            this._setActiveField(firstIncomplete.id, { focus: false, scroll: false });
        }
    }

    _findFirstIncompleteActionableField() {
        return this._getOrderedActionableFields().find((field) => !this._isFieldComplete(field)) || false;
    }

    _getNextIncompleteActionableField(fromFieldId = false) {
        const actionableFields = this._getOrderedActionableFields();
        if (!actionableFields.length) {
            return false;
        }
        const currentIndex = actionableFields.findIndex((field) => field.id === Number(fromFieldId));
        if (currentIndex < 0) {
            return actionableFields.find((field) => !this._isFieldComplete(field)) || false;
        }
        for (let offset = 1; offset <= actionableFields.length; offset += 1) {
            const candidate = actionableFields[(currentIndex + offset) % actionableFields.length];
            if (!this._isFieldComplete(candidate)) {
                return candidate;
            }
        }
        return false;
    }

    _getSiblingActionableField(currentFieldId, direction) {
        const actionableFields = this._getOrderedActionableFields();
        const currentIndex = actionableFields.findIndex((field) => field.id === Number(currentFieldId));
        if (currentIndex < 0) {
            return false;
        }
        return actionableFields[currentIndex + direction] || false;
    }

    _scrollFieldIntoView(fieldId) {
        const fieldNode = this._getFieldNode(fieldId);
        fieldNode?.scrollIntoView?.({ block: "center", inline: "nearest" });
    }

    _focusFieldControl(fieldId) {
        const control = this._getPrimaryControl(fieldId);
        if (!control?.focus) {
            return;
        }
        try {
            control.focus({ preventScroll: true });
        } catch {
            control.focus();
        }
    }

    async _createCaptureAttachment(field, payload) {
        const route = `/my/sign/${this.session.signerId}/field/${field.id}/payload/create`;
        const requestPayload = {
            value: payload,
        };
        if (this.session.accessToken) {
            requestPayload.access_token = this.session.accessToken;
        }
        try {
            return await rpc(route, requestPayload);
        } catch {
            return {
                valid: false,
                errorCode: "attachment_create_failed",
            };
        }
    }

    _applyCapturePayload(fieldId, payload) {
        const field = this._getField(fieldId);
        if (!field || !payload) {
            return;
        }
        field.value = {
            method: payload.method || "draw",
            display_name: payload.display_name || "",
            signature_image_mime_type: payload.signature_image_mime_type || "",
            signature_image_byte_size: Number.parseInt(payload.signature_image_byte_size, 10) || 0,
            signed_payload_attachment_id:
                Number.parseInt(payload.signed_payload_attachment_id, 10) || false,
        };
        field.preview_data_url = payload.preview_data_url || "";
        field.has_value = Boolean(field.value.signed_payload_attachment_id);
        this.touchedFieldIds.add(field.id);
        this.invalidFieldIds.delete(field.id);
        this._renderFieldBody(field.id);
        this._syncFieldState(field.id);
        this._updateNextFieldButtonState();
        const nextField = this._getNextIncompleteActionableField(field.id);
        if (nextField && nextField.id !== field.id) {
            this._setActiveField(nextField.id, { focus: true, scroll: true });
            return;
        }
        this._setActiveField(field.id, { focus: true, scroll: false });
    }

    _openCaptureDialog(field) {
        if (!field || !this._isActionableField(field)) {
            return;
        }
        openSignatureAdoptionDialog(this.session.services.dialog, {
            defaultMethod: field.value?.method || "draw",
            defaultName: field.value?.display_name || "",
            signatureType: field.type,
            attachmentNamePrefix: field.type === "stamp" ? "open_sign_stamp" : "open_sign_signature",
            createAttachment: async (payload) => this._createCaptureAttachment(field, payload),
            adoptSignature: async (payload) => {
                this._applyCapturePayload(field.id, payload);
            },
        });
    }

    _setActiveField(fieldId, { focus = false, scroll = true } = {}) {
        const field = this._getField(fieldId);
        if (!field) {
            return false;
        }
        this.activeFieldId = field.id;
        this._syncAllFieldStates();
        if (scroll) {
            this._scrollFieldIntoView(field.id);
        }
        if (focus && this._isActionableField(field)) {
            this._focusFieldControl(field.id);
        }
        return true;
    }

    _updateNextFieldButtonState() {
        if (!this.nextFieldButton) {
            return;
        }
        this.nextFieldButton.disabled = !this.surfaceInteractive
            || !this._getNextIncompleteActionableField(this.activeFieldId);
    }

    _updateSummaryAvailability() {
        if (!this.summaryRoot) {
            return;
        }
        for (const summaryNode of this.summaryRoot.querySelectorAll(".o_open_sign_field_summary_item")) {
            summaryNode.disabled = !this.surfaceInteractive;
            summaryNode.classList.toggle("o_is_disabled", !this.surfaceInteractive);
        }
    }

    _revalidateFieldIfNeeded(fieldId) {
        const field = this._getField(fieldId);
        if (!field || !this.invalidFieldIds.has(fieldId)) {
            return;
        }
        const result = this._validateField(field, { enforceRequired: Boolean(field.required) });
        if (result.valid) {
            this.invalidFieldIds.delete(fieldId);
        }
    }

    _onFieldClick(event) {
        const fieldNode = event.target.closest(".o_open_sign_field");
        if (!fieldNode) {
            return;
        }
        const fieldId = Number(fieldNode.dataset.fieldId || 0);
        const field = this._getField(fieldId);
        if (!field) {
            return;
        }
        if (CAPTURE_FIELD_TYPES.has(field.type) && this._isActionableField(field)) {
            event.preventDefault();
            this._setActiveField(fieldId, { focus: false, scroll: false });
            this._focusFieldControl(fieldId);
            this._openCaptureDialog(field);
            return;
        }
        const focus = this._isActionableField(field) && !isDirectControlTarget(event.target);
        this._setActiveField(fieldId, { focus, scroll: false });
    }

    _onFieldInput(event) {
        const fieldNode = event.target.closest(".o_open_sign_field");
        if (!fieldNode) {
            return;
        }
        const fieldId = Number(fieldNode.dataset.fieldId || 0);
        if (!fieldId) {
            return;
        }
        this.touchedFieldIds.add(fieldId);
        this._revalidateFieldIfNeeded(fieldId);
        this._syncFieldState(fieldId);
        this._updateNextFieldButtonState();
    }

    _onFieldKeydown(event) {
        if (!this._isEditableSession() || event.key !== "Tab" || event.altKey || event.ctrlKey || event.metaKey) {
            return;
        }
        const fieldNode = event.target.closest(".o_open_sign_field");
        if (!fieldNode) {
            return;
        }
        const currentFieldId = Number(fieldNode.dataset.fieldId || 0);
        const currentField = this._getField(currentFieldId);
        if (!this._isActionableField(currentField)) {
            return;
        }
        const targetField = this._getSiblingActionableField(currentFieldId, event.shiftKey ? -1 : 1);
        if (!targetField) {
            return;
        }
        event.preventDefault();
        this._setActiveField(targetField.id, { focus: true, scroll: true });
    }

    _onSummaryClick(event) {
        if (!this.surfaceInteractive) {
            return;
        }
        const summaryItem = event.target.closest(".o_open_sign_field_summary_item");
        if (!summaryItem) {
            return;
        }
        event.preventDefault();
        const fieldId = Number(summaryItem.dataset.fieldId || 0);
        const field = this._getField(fieldId);
        if (!field) {
            return;
        }
        this._setActiveField(fieldId, {
            focus: this._isActionableField(field),
            scroll: true,
        });
    }

    _onNextFieldClick(event) {
        event.preventDefault();
        if (!this.surfaceInteractive) {
            return;
        }
        const nextField = this._getNextIncompleteActionableField(this.activeFieldId);
        if (!nextField) {
            return;
        }
        this._setActiveField(nextField.id, { focus: true, scroll: true });
    }

    validateActionableFields({ enforceRequired }) {
        const actionableFields = this._getActionableFields();
        this.invalidFieldIds.clear();
        let firstInvalid = false;
        for (const field of actionableFields) {
            const result = this._validateField(field, { enforceRequired });
            if (result.valid) {
                continue;
            }
            this.invalidFieldIds.add(field.id);
            if (!firstInvalid) {
                firstInvalid = {
                    field,
                    message: this._formatValidationError(field, result.errorCode),
                };
            }
        }
        this._syncAllFieldStates();
        if (!firstInvalid) {
            return { valid: true, message: false };
        }
        this._setActiveField(firstInvalid.field.id, { focus: true, scroll: true });
        return {
            valid: false,
            fieldId: firstInvalid.field.id,
            message: firstInvalid.message,
        };
    }
}
