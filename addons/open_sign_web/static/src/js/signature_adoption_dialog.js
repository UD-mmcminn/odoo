/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { NameAndSignature } from "@web/core/signature/name_and_signature";
import { useService } from "@web/core/utils/hooks";

import { Component, useState } from "@odoo/owl";

const SIGNATURE_ADOPTION_METHODS = Object.freeze(["draw", "type", "upload"]);
const METHOD_TO_SIGNATURE_MODE = Object.freeze({
    draw: "draw",
    type: "auto",
    upload: "load",
});
const SIGNATURE_MODE_TO_METHOD = Object.freeze({
    draw: "draw",
    auto: "type",
    load: "upload",
});
const DEFAULT_ALLOWED_MIME_TYPES = Object.freeze([
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/svg+xml",
]);
const DEFAULT_MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
const DATA_URL_RE = /^data:([^;,]+);base64,([A-Za-z0-9+/]+={0,2})$/;
const DEFAULT_ATTACHMENT_RES_MODEL = "open.sign.request.value";
const DEFAULT_ATTACHMENT_NAME_PREFIX = "open_sign_signature";
const MIME_TYPE_EXTENSIONS = Object.freeze({
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/svg+xml": "svg",
});

const METHOD_LABELS = Object.freeze({
    draw: _t("Draw"),
    type: _t("Type"),
    upload: _t("Upload"),
});

function normalizeMethodInput(method) {
    return String(method || "").trim().toLowerCase();
}

function asPositiveInteger(value) {
    const parsed = Number.parseInt(value, 10);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function normalizeAttachmentContext(context) {
    const baseContext = context && typeof context === "object" ? context : {};
    return Object.fromEntries(
        Object.entries(baseContext).filter(([key]) => !String(key).startsWith("default_"))
    );
}

function normalizeMimeTypes(mimeTypes) {
    const candidates = Array.isArray(mimeTypes) ? mimeTypes : [];
    const normalized = candidates
        .map((mimeType) => String(mimeType || "").trim().toLowerCase())
        .filter(Boolean);
    return normalized.length ? normalized : [...DEFAULT_ALLOWED_MIME_TYPES];
}

function parseDataUrl(signatureImage) {
    const source = String(signatureImage || "").trim();
    if (!source) {
        return null;
    }
    const matches = DATA_URL_RE.exec(source);
    if (!matches) {
        return null;
    }
    const mimeType = matches[1].toLowerCase();
    const base64Data = matches[2];
    const padding = base64Data.endsWith("==") ? 2 : base64Data.endsWith("=") ? 1 : 0;
    const byteSize = Math.max(0, Math.floor((base64Data.length * 3) / 4) - padding);
    return {
        dataUrl: source,
        mimeType,
        base64Data,
        byteSize,
    };
}

export function getSignatureAdoptionMethods() {
    return [...SIGNATURE_ADOPTION_METHODS];
}

export function normalizeSignatureAdoptionMethod(method, fallback = "draw") {
    const normalizedFallback = normalizeMethodInput(fallback);
    const fallbackValue = SIGNATURE_ADOPTION_METHODS.includes(normalizedFallback)
        ? normalizedFallback
        : "draw";
    const normalizedMethod = normalizeMethodInput(method);
    return SIGNATURE_ADOPTION_METHODS.includes(normalizedMethod) ? normalizedMethod : fallbackValue;
}

export function getNameAndSignatureMode(method) {
    const normalizedMethod = normalizeSignatureAdoptionMethod(method);
    return METHOD_TO_SIGNATURE_MODE[normalizedMethod];
}

export function getSignatureAdoptionMethodFromMode(mode, fallback = "draw") {
    const normalizedMode = normalizeMethodInput(mode);
    if (SIGNATURE_MODE_TO_METHOD[normalizedMode]) {
        return SIGNATURE_MODE_TO_METHOD[normalizedMode];
    }
    return normalizeSignatureAdoptionMethod(fallback);
}

export function validateSignatureImageDataUrl(signatureImage, options = {}) {
    const parsedDataUrl = parseDataUrl(signatureImage);
    if (!parsedDataUrl) {
        return {
            valid: false,
            errorCode: "invalid_signature_image_data_url",
        };
    }
    const allowedMimeTypes = new Set(normalizeMimeTypes(options.allowedMimeTypes));
    if (!allowedMimeTypes.has(parsedDataUrl.mimeType)) {
        return {
            valid: false,
            errorCode: "unsupported_signature_image_type",
        };
    }
    const maxUploadBytes = Number.isFinite(Number(options.maxUploadBytes))
        ? Math.max(1, Number(options.maxUploadBytes))
        : DEFAULT_MAX_UPLOAD_BYTES;
    if (parsedDataUrl.byteSize > maxUploadBytes) {
        return {
            valid: false,
            errorCode: "signature_image_too_large",
        };
    }
    return {
        valid: true,
        errorCode: null,
        dataUrl: parsedDataUrl.dataUrl,
        mimeType: parsedDataUrl.mimeType,
        byteSize: parsedDataUrl.byteSize,
        base64Data: parsedDataUrl.base64Data,
    };
}

export function buildSignatureAdoptionPayload(input = {}, options = {}) {
    const method = normalizeSignatureAdoptionMethod(input.method);
    const displayName = String(input.displayName || input.display_name || "").trim();
    if (!displayName) {
        return {
            valid: false,
            errorCode: "missing_display_name",
        };
    }
    const imageValidation = validateSignatureImageDataUrl(input.signatureImage, options);
    if (!imageValidation.valid) {
        return imageValidation;
    }
    return {
        valid: true,
        errorCode: null,
        value: {
            method,
            display_name: displayName,
            signature_image: imageValidation.dataUrl,
            signature_image_mime_type: imageValidation.mimeType,
            signature_image_byte_size: imageValidation.byteSize,
        },
    };
}

export function buildSignatureAttachmentCreateVals(payload = {}, options = {}) {
    const signatureImage = payload.signature_image || payload.signatureImage;
    const imageValidation = validateSignatureImageDataUrl(signatureImage, options);
    if (!imageValidation.valid) {
        return imageValidation;
    }
    const method = normalizeSignatureAdoptionMethod(payload.method);
    const prefix = String(options.attachmentNamePrefix || DEFAULT_ATTACHMENT_NAME_PREFIX)
        .trim()
        .replace(/[^a-zA-Z0-9._-]+/g, "_")
        .replace(/^_+|_+$/g, "");
    const normalizedPrefix = prefix || DEFAULT_ATTACHMENT_NAME_PREFIX;
    const extension = MIME_TYPE_EXTENSIONS[imageValidation.mimeType] || "bin";
    const filename = `${normalizedPrefix}_${method}_${Date.now()}.${extension}`;
    const values = {
        name: filename,
        mimetype: imageValidation.mimeType,
        datas: imageValidation.base64Data,
        res_model: options.attachmentResModel || DEFAULT_ATTACHMENT_RES_MODEL,
    };
    const attachmentResId = asPositiveInteger(options.attachmentResId);
    if (attachmentResId) {
        values.res_id = attachmentResId;
    }
    const companyId = asPositiveInteger(options.companyId);
    if (companyId) {
        values.company_id = companyId;
    }
    return {
        valid: true,
        errorCode: null,
        values,
        mimeType: imageValidation.mimeType,
        byteSize: imageValidation.byteSize,
    };
}

export async function createSignedPayloadAttachment(orm, payload = {}, options = {}) {
    if (!orm || typeof orm.create !== "function") {
        return {
            valid: false,
            errorCode: "attachment_create_failed",
        };
    }
    const attachmentValues = buildSignatureAttachmentCreateVals(payload, options);
    if (!attachmentValues.valid) {
        return attachmentValues;
    }
    try {
        const createOptions = {};
        const context = normalizeAttachmentContext(options.attachmentContext);
        if (Object.keys(context).length) {
            createOptions.context = context;
        }
        const [attachmentId] = await orm.create("ir.attachment", [attachmentValues.values], createOptions);
        const normalizedAttachmentId = asPositiveInteger(attachmentId);
        if (!normalizedAttachmentId) {
            return {
                valid: false,
                errorCode: "attachment_create_failed",
            };
        }
        return {
            valid: true,
            errorCode: null,
            attachmentId: normalizedAttachmentId,
            mimeType: attachmentValues.mimeType,
            byteSize: attachmentValues.byteSize,
        };
    } catch {
        return {
            valid: false,
            errorCode: "attachment_create_failed",
        };
    }
}

export function getSignatureAdoptionErrorMessage(errorCode) {
    switch (errorCode) {
        case "missing_display_name":
            return _t("Please provide the signer name before adopting a signature.");
        case "unsupported_signature_image_type":
            return _t("Uploaded signature image type is not supported.");
        case "signature_image_too_large":
            return _t("Uploaded signature image exceeds the allowed size limit.");
        case "attachment_create_failed":
            return _t("Unable to store the signature attachment.");
        case "invalid_signature_image_data_url":
        default:
            return _t("Signature image is missing or invalid.");
    }
}

export class SignatureAdoptionDialog extends Component {
    static template = "open_sign_web.SignatureAdoptionDialog";
    static components = { Dialog, NameAndSignature };
    static props = {
        defaultName: { type: String, optional: true },
        defaultMethod: { type: String, optional: true },
        signatureType: { type: String, optional: true },
        fontColor: { type: String, optional: true },
        displaySignatureRatio: { type: Number, optional: true },
        consentText: { type: String, optional: true },
        allowedMimeTypes: { type: Array, optional: true },
        maxUploadBytes: { type: Number, optional: true },
        attachmentResModel: { type: String, optional: true },
        attachmentResId: { type: Number, optional: true },
        attachmentNamePrefix: { type: String, optional: true },
        attachmentContext: { type: Object, optional: true },
        companyId: { type: Number, optional: true },
        adoptSignature: Function,
        close: Function,
    };
    static defaultProps = {
        defaultName: "",
        defaultMethod: "draw",
        signatureType: "signature",
        fontColor: "DarkBlue",
        displaySignatureRatio: 3.0,
        consentText: "",
        allowedMimeTypes: [...DEFAULT_ALLOWED_MIME_TYPES],
        maxUploadBytes: DEFAULT_MAX_UPLOAD_BYTES,
        attachmentResModel: DEFAULT_ATTACHMENT_RES_MODEL,
        attachmentNamePrefix: DEFAULT_ATTACHMENT_NAME_PREFIX,
        attachmentContext: {},
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            method: normalizeSignatureAdoptionMethod(this.props.defaultMethod),
            errorCode: null,
            isSubmitting: false,
        });
        this.signature = useState({
            name: this.props.defaultName,
            isSignatureEmpty: true,
            getSignatureImage: () => "",
            resetSignature: () => {},
        });
    }

    get selectedMethodLabel() {
        return METHOD_LABELS[this.state.method] || METHOD_LABELS.draw;
    }

    get consentMessage() {
        return (
            this.props.consentText ||
            _t(
                "By clicking Adopt Signature, I agree this electronic signature may represent my handwritten signature for legally binding documents."
            )
        );
    }

    get adoptButtonDisabled() {
        return (
            this.state.isSubmitting ||
            this.signature.isSignatureEmpty ||
            !String(this.signature.name || "").trim()
        );
    }

    get errorMessage() {
        return this.state.errorCode ? getSignatureAdoptionErrorMessage(this.state.errorCode) : "";
    }

    get nameAndSignatureProps() {
        return {
            signature: this.signature,
            signatureType: this.props.signatureType,
            fontColor: this.props.fontColor,
            displaySignatureRatio: this.props.displaySignatureRatio,
            mode: getNameAndSignatureMode(this.state.method),
            onSignatureChange: (mode) => {
                this.state.method = getSignatureAdoptionMethodFromMode(mode, this.state.method);
                this.state.errorCode = null;
            },
        };
    }

    async onClickAdopt() {
        if (this.state.isSubmitting) {
            return;
        }
        const payloadResult = buildSignatureAdoptionPayload(
            {
                method: this.state.method,
                displayName: this.signature.name,
                signatureImage: this.signature.getSignatureImage(),
            },
            {
                allowedMimeTypes: this.props.allowedMimeTypes,
                maxUploadBytes: this.props.maxUploadBytes,
            }
        );
        if (!payloadResult.valid) {
            this.state.errorCode = payloadResult.errorCode;
            return;
        }
        this.state.isSubmitting = true;
        this.state.errorCode = null;
        const attachmentResult = await createSignedPayloadAttachment(this.orm, payloadResult.value, {
            allowedMimeTypes: this.props.allowedMimeTypes,
            maxUploadBytes: this.props.maxUploadBytes,
            attachmentResModel: this.props.attachmentResModel,
            attachmentResId: this.props.attachmentResId,
            attachmentNamePrefix: this.props.attachmentNamePrefix,
            attachmentContext: this.props.attachmentContext,
            companyId: this.props.companyId,
        });
        if (!attachmentResult.valid) {
            this.state.errorCode = attachmentResult.errorCode;
            this.state.isSubmitting = false;
            return;
        }
        const normalizedPayload = {
            method: payloadResult.value.method,
            display_name: payloadResult.value.display_name,
            signature_image_mime_type: attachmentResult.mimeType,
            signature_image_byte_size: attachmentResult.byteSize,
            signed_payload_attachment_id: attachmentResult.attachmentId,
        };
        try {
            await this.props.adoptSignature(normalizedPayload);
            this.props.close();
        } catch {
            this.state.errorCode = "attachment_create_failed";
        } finally {
            this.state.isSubmitting = false;
        }
    }
}

export function openSignatureAdoptionDialog(dialogService, options = {}) {
    if (!dialogService || typeof dialogService.add !== "function") {
        throw new Error("A valid dialog service is required to open SignatureAdoptionDialog.");
    }
    dialogService.add(SignatureAdoptionDialog, options);
}
