/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { Interaction } from "@web/public/interaction";
import { redirect } from "@web/core/utils/urls";

import { OpenSignPortalPdfSurface } from "@open_sign_portal/interactions/portal_pdf_surface";

export class OpenSignPortalSession extends Interaction {
    static selector = ".o_open_sign_session";

    dynamicContent = {
        ".o_open_sign_save": { "t-on-click.prevent": this.locked(this.onClickSave, true) },
        ".o_open_sign_submit": { "t-on-click.prevent": this.locked(this.onClickSubmit, true) },
        ".o_open_sign_decline_confirm": { "t-on-click.prevent": this.locked(this.onClickDecline, true) },
        ".o_open_sign_otp_request": { "t-on-click.prevent": this.locked(this.onClickOtpRequest, true) },
        ".o_open_sign_otp_verify": { "t-on-click.prevent": this.locked(this.onClickOtpVerify, true) },
    };

    setup() {
        this.signerId = this.el.dataset.signerId || "";
        this.saveUrl = this.el.dataset.saveUrl;
        this.submitUrl = this.el.dataset.submitUrl;
        this.declineUrl = this.el.dataset.declineUrl;
        this.otpRequestUrl = this.el.dataset.otpRequestUrl;
        this.otpVerifyUrl = this.el.dataset.otpVerifyUrl;
        this.accessToken = this.el.dataset.accessToken || false;
        this.requestRevision = Number.parseInt(this.el.dataset.requestRevision || "0", 10) || 0;
        this.consentHash = this.el.dataset.consentHash || "";

        this.errorNode = this.el.querySelector(".o_open_sign_error");
        this.successNode = this.el.querySelector(".o_open_sign_success");
        this.statusNode = this.el.querySelector(".o_open_sign_request_status");
        this.consentCheckbox = this.el.querySelector(".o_open_sign_consent");
        this.declineReasonInput = this.el.parentElement?.querySelector(".o_open_sign_decline_reason")
            || this.el.querySelector(".o_open_sign_decline_reason");
        this.otpCodeInput = this.el.querySelector(".o_open_sign_otp_code");
        this.pdfSurface = new OpenSignPortalPdfSurface(this);
    }

    async willStart() {
        await super.willStart();
        await this.pdfSurface.willStart();
    }

    start() {
        this.pdfSurface.start();
    }

    _validateBeforeMutation({ enforceRequired }) {
        return this.pdfSurface.validateActionableFields({ enforceRequired });
    }

    _pendingIdempotencyStorageKey(endpoint) {
        if (!this.signerId || !endpoint) {
            return false;
        }
        return `open_sign:${this.signerId}:${endpoint}:pending_idempotency_key`;
    }

    _getPendingIdempotencyKey(endpoint) {
        const storageKey = this._pendingIdempotencyStorageKey(endpoint);
        if (!storageKey) {
            return false;
        }
        try {
            return window.sessionStorage?.getItem(storageKey) || false;
        } catch {
            return false;
        }
    }

    _setPendingIdempotencyKey(endpoint, value) {
        const storageKey = this._pendingIdempotencyStorageKey(endpoint);
        if (!storageKey) {
            return;
        }
        try {
            window.sessionStorage?.setItem(storageKey, value);
        } catch {
            // Ignore storage failures and fall back to per-request keys.
        }
    }

    _clearPendingIdempotencyKey(endpoint) {
        const storageKey = this._pendingIdempotencyStorageKey(endpoint);
        if (!storageKey) {
            return;
        }
        try {
            window.sessionStorage?.removeItem(storageKey);
        } catch {
            // Ignore storage failures and fall back to per-request keys.
        }
    }

    _getOrCreatePendingIdempotencyKey(endpoint) {
        const existingKey = this._getPendingIdempotencyKey(endpoint);
        if (existingKey) {
            return existingKey;
        }
        const newKey = this._newIdempotencyKey();
        this._setPendingIdempotencyKey(endpoint, newKey);
        return newKey;
    }

    _shouldRetainPendingIdempotencyKey(response) {
        return Boolean(response?.ok !== true && response?.error_code === "request_locked");
    }

    _finalizePendingIdempotencyKey(endpoint, response) {
        if (!endpoint || this._shouldRetainPendingIdempotencyKey(response)) {
            return;
        }
        this._clearPendingIdempotencyKey(endpoint);
    }

    _newIdempotencyKey() {
        if (window.crypto?.randomUUID) {
            return window.crypto.randomUUID();
        }
        const template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx";
        return template.replace(/[xy]/g, (char) => {
            const rand = Math.floor(Math.random() * 16);
            const value = char === "x" ? rand : (rand & 0x3) | 0x8;
            return value.toString(16);
        });
    }

    _collectValueForField(fieldNode) {
        const fieldType = fieldNode.dataset.fieldType;
        if (["text", "name", "company", "initials", "email", "phone", "multiline", "selection"].includes(fieldType)) {
            const input = fieldNode.querySelector(".o_open_sign_input");
            return input ? input.value : "";
        }
        if (fieldType === "radio") {
            const checked = fieldNode.querySelector(".o_open_sign_radio:checked");
            return checked ? checked.value : false;
        }
        if (fieldType === "checkbox") {
            const checkbox = fieldNode.querySelector(".o_open_sign_checkbox");
            return Boolean(checkbox?.checked);
        }
        if (fieldType === "date") {
            const input = fieldNode.querySelector(".o_open_sign_input");
            return input?.value || false;
        }
        if (fieldType === "strikethrough") {
            const checkbox = fieldNode.querySelector(".o_open_sign_checkbox");
            return Boolean(checkbox?.checked);
        }
        if (["signature", "stamp"].includes(fieldType)) {
            const fieldId = Number.parseInt(fieldNode.dataset.fieldId || "0", 10);
            return fieldId ? this.pdfSurface.getFieldValuePayload(fieldId) : false;
        }
        return false;
    }

    _collectValuesPayload() {
        const values = [];
        for (const fieldNode of this.el.querySelectorAll(".o_open_sign_field")) {
            const fieldId = Number.parseInt(fieldNode.dataset.fieldId || "0", 10);
            if (!fieldId || fieldNode.dataset.editable !== "true") {
                continue;
            }
            values.push({
                field_id: fieldId,
                value: this._collectValueForField(fieldNode),
            });
        }
        return values;
    }

    _buildPayload({ endpoint = false } = {}) {
        const payload = {
            values: this._collectValuesPayload(),
            idempotency_key: endpoint
                ? this._getOrCreatePendingIdempotencyKey(endpoint)
                : this._newIdempotencyKey(),
            request_revision: this.requestRevision,
        };
        if (this.accessToken) {
            payload.access_token = this.accessToken;
        }
        return payload;
    }

    _buildDeclinePayload({ endpoint = false } = {}) {
        const payload = {
            idempotency_key: endpoint
                ? this._getOrCreatePendingIdempotencyKey(endpoint)
                : this._newIdempotencyKey(),
            request_revision: this.requestRevision,
            reason: this.declineReasonInput?.value || "",
        };
        if (this.accessToken) {
            payload.access_token = this.accessToken;
        }
        return payload;
    }

    _buildOtpRequestPayload() {
        const payload = {
            request_revision: this.requestRevision,
        };
        if (this.accessToken) {
            payload.access_token = this.accessToken;
        }
        return payload;
    }

    _buildOtpVerifyPayload() {
        const payload = {
            request_revision: this.requestRevision,
            code: this.otpCodeInput?.value || "",
        };
        if (this.accessToken) {
            payload.access_token = this.accessToken;
        }
        return payload;
    }

    _resetAlerts() {
        this.errorNode?.classList.add("d-none");
        this.successNode?.classList.add("d-none");
    }

    _showError(message) {
        if (!this.errorNode) {
            return;
        }
        this.errorNode.textContent = message || "An unexpected error occurred.";
        this.errorNode.classList.remove("d-none");
    }

    _showSuccess(message) {
        if (!this.successNode) {
            return;
        }
        this.successNode.textContent = message;
        this.successNode.classList.remove("d-none");
    }

    _updateRevisionAndStatus(response) {
        if (Number.isInteger(response?.request_revision)) {
            this.requestRevision = response.request_revision;
            this.el.dataset.requestRevision = String(this.requestRevision);
        }
        if (this.statusNode && response?.state) {
            this.statusNode.textContent = response.state;
        }
    }

    async onClickSave() {
        this._resetAlerts();
        const validation = this._validateBeforeMutation({ enforceRequired: false });
        if (!validation.valid) {
            this._showError(validation.message);
            return;
        }
        const payload = this._buildPayload();
        const response = await rpc(this.saveUrl, payload);
        if (!response?.ok) {
            this._showError(response?.message);
            return;
        }
        this._updateRevisionAndStatus(response);
        this._showSuccess("Draft saved.");
    }

    async onClickSubmit() {
        this._resetAlerts();
        const validation = this._validateBeforeMutation({ enforceRequired: true });
        if (!validation.valid) {
            this._showError(validation.message);
            return;
        }
        const payload = this._buildPayload({ endpoint: "submit" });
        payload.consent = {
            accepted: Boolean(this.consentCheckbox?.checked),
            text_hash: this.consentHash,
            timezone: new Intl.DateTimeFormat().resolvedOptions().timeZone || "",
        };
        let response;
        try {
            response = await rpc(this.submitUrl, payload);
        } catch {
            this._showError("The request could not be confirmed. Retry may complete the earlier action.");
            return;
        }
        this._finalizePendingIdempotencyKey("submit", response);
        if (!response?.ok) {
            this._showError(response?.message);
            return;
        }
        this._updateRevisionAndStatus(response);
        if (response.force_refresh && response.redirect_url) {
            redirect(response.redirect_url);
            return;
        }
        if (response.force_refresh) {
            window.location.reload();
            return;
        }
        this._showSuccess("Submission completed.");
    }

    async onClickDecline() {
        this._resetAlerts();
        if (!this.declineUrl) {
            this._showError("Decline is not available.");
            return;
        }
        let response;
        try {
            response = await rpc(this.declineUrl, this._buildDeclinePayload({ endpoint: "decline" }));
        } catch {
            this._showError("The request could not be confirmed. Retry may complete the earlier action.");
            return;
        }
        this._finalizePendingIdempotencyKey("decline", response);
        if (!response?.ok) {
            this._showError(response?.message);
            return;
        }
        this._updateRevisionAndStatus(response);
        if (response.force_refresh && response.redirect_url) {
            redirect(response.redirect_url);
            return;
        }
        if (response.force_refresh) {
            window.location.reload();
            return;
        }
        this._showSuccess("Decline recorded.");
    }

    async onClickOtpRequest() {
        this._resetAlerts();
        if (!this.otpRequestUrl) {
            this._showError("Verification request is not available.");
            return;
        }
        const response = await rpc(this.otpRequestUrl, this._buildOtpRequestPayload());
        if (!response?.ok) {
            this._showError(response?.message);
            return;
        }
        this._updateRevisionAndStatus(response);
        if (response.force_refresh && response.redirect_url) {
            redirect(response.redirect_url);
            return;
        }
        if (response.force_refresh) {
            window.location.reload();
            return;
        }
        this._showSuccess("Verification code queued.");
    }

    async onClickOtpVerify() {
        this._resetAlerts();
        if (!this.otpVerifyUrl) {
            this._showError("Verification is not available.");
            return;
        }
        const response = await rpc(this.otpVerifyUrl, this._buildOtpVerifyPayload());
        if (!response?.ok) {
            this._showError(response?.message);
            return;
        }
        this._updateRevisionAndStatus(response);
        if (response.force_refresh && response.redirect_url) {
            redirect(response.redirect_url);
            return;
        }
        if (response.force_refresh) {
            window.location.reload();
            return;
        }
        this._showSuccess("Email verification complete.");
    }
}

registry.category("public.interactions").add("open_sign_portal.session", OpenSignPortalSession);
