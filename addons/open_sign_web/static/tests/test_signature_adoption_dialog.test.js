import { describe, expect, test } from "@odoo/hoot";

import {
    buildSignatureAdoptionPayload,
    buildSignatureAttachmentCreateVals,
    createSignedPayloadAttachment,
    getSignatureAdoptionCopy,
    getSignatureAdoptionErrorMessage,
    getNameAndSignatureMode,
    getSignatureAdoptionMethodFromMode,
    getSignatureAdoptionMethods,
    normalizeSignatureAdoptionMethod,
    validateSignatureImageDataUrl,
} from "@open_sign_web/js/signature_adoption_dialog";

describe.current.tags("headless", "open_sign_web");

function toPlainCopy(copy) {
    return {
        title: String.prototype.valueOf.call(copy.title),
        actionLabel: String.prototype.valueOf.call(copy.actionLabel),
        noun: String.prototype.valueOf.call(copy.noun),
        namePrefix: copy.namePrefix,
    };
}

const VALID_SIGNATURE_DATA_URL =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4//8/AwAI/AL+X2VINwAAAABJRU5ErkJggg==";

test("signature adoption methods stay canonical and immutable", () => {
    const methods = getSignatureAdoptionMethods();
    expect(methods).toEqual(["draw", "type", "upload"]);
    methods.push("other");
    expect(getSignatureAdoptionMethods()).toEqual(["draw", "type", "upload"]);
});

test("method normalization and mode mapping remain deterministic", () => {
    expect(normalizeSignatureAdoptionMethod("TYPE")).toBe("type");
    expect(normalizeSignatureAdoptionMethod("unknown")).toBe("draw");
    expect(normalizeSignatureAdoptionMethod("unknown", "upload")).toBe("upload");

    expect(getNameAndSignatureMode("draw")).toBe("draw");
    expect(getNameAndSignatureMode("type")).toBe("auto");
    expect(getNameAndSignatureMode("upload")).toBe("load");

    expect(getSignatureAdoptionMethodFromMode("draw")).toBe("draw");
    expect(getSignatureAdoptionMethodFromMode("auto")).toBe("type");
    expect(getSignatureAdoptionMethodFromMode("load")).toBe("upload");
    expect(getSignatureAdoptionMethodFromMode("other", "type")).toBe("type");
});

test("signature adoption copy switches cleanly for stamp capture", () => {
    expect(toPlainCopy(getSignatureAdoptionCopy("signature"))).toEqual({
        title: "Adopt Signature",
        actionLabel: "Adopt Signature",
        noun: "signature",
        namePrefix: "open_sign_signature",
    });
    expect(toPlainCopy(getSignatureAdoptionCopy("stamp"))).toEqual({
        title: "Adopt Stamp",
        actionLabel: "Adopt Stamp",
        noun: "stamp",
        namePrefix: "open_sign_stamp",
    });
});

test("signature adoption error messages stay deterministic for portal capture codes", () => {
    expect(String.prototype.valueOf.call(getSignatureAdoptionErrorMessage("invalid_capture_field"))).toBe(
        "This signature field is no longer available. Refresh the page and try again."
    );
    expect(String.prototype.valueOf.call(getSignatureAdoptionErrorMessage("readonly_session"))).toBe(
        "This signing session is read-only."
    );
    expect(String.prototype.valueOf.call(getSignatureAdoptionErrorMessage("request_locked"))).toBe(
        "The signing request is currently locked. Try again."
    );
    expect(String.prototype.valueOf.call(getSignatureAdoptionErrorMessage("signing_order_blocked"))).toBe(
        "Another signer must complete before your turn begins."
    );
    expect(String.prototype.valueOf.call(getSignatureAdoptionErrorMessage("invalid_token"))).toBe(
        "Invalid or expired signing link."
    );
    expect(String.prototype.valueOf.call(getSignatureAdoptionErrorMessage("expired_token"))).toBe(
        "This signing link has expired. Request a new link."
    );
});

test("validateSignatureImageDataUrl validates mime type and size", () => {
    const valid = validateSignatureImageDataUrl(VALID_SIGNATURE_DATA_URL);
    expect(valid.valid).toBe(true);
    expect(valid.mimeType).toBe("image/png");
    expect(valid.byteSize > 0).toBe(true);

    const unsupportedMime = validateSignatureImageDataUrl(
        "data:image/gif;base64,R0lGODlhAQABAIAAAAUEBA==",
        { allowedMimeTypes: ["image/png"] }
    );
    expect(unsupportedMime).toEqual({
        valid: false,
        errorCode: "unsupported_signature_image_type",
    });

    const tooLarge = validateSignatureImageDataUrl(VALID_SIGNATURE_DATA_URL, {
        maxUploadBytes: 10,
    });
    expect(tooLarge).toEqual({
        valid: false,
        errorCode: "signature_image_too_large",
    });

    const invalid = validateSignatureImageDataUrl("not-a-data-url");
    expect(invalid).toEqual({
        valid: false,
        errorCode: "invalid_signature_image_data_url",
    });
});

test("buildSignatureAdoptionPayload returns normalized payload", () => {
    const payload = buildSignatureAdoptionPayload({
        method: "TYPE",
        displayName: "  Alice Signer  ",
        signatureImage: VALID_SIGNATURE_DATA_URL,
    });
    expect(payload.valid).toBe(true);
    expect(payload.value.method).toBe("type");
    expect(payload.value.display_name).toBe("Alice Signer");
    expect(payload.value.signature_image_mime_type).toBe("image/png");
    expect(payload.value.signature_image_byte_size > 0).toBe(true);
});

test("buildSignatureAdoptionPayload rejects missing signer name and bad image", () => {
    const missingName = buildSignatureAdoptionPayload({
        method: "draw",
        displayName: "   ",
        signatureImage: VALID_SIGNATURE_DATA_URL,
    });
    expect(missingName).toEqual({
        valid: false,
        errorCode: "missing_display_name",
    });

    const missingImage = buildSignatureAdoptionPayload({
        method: "draw",
        displayName: "Alice",
        signatureImage: "",
    });
    expect(missingImage).toEqual({
        valid: false,
        errorCode: "invalid_signature_image_data_url",
    });
});

test("buildSignatureAttachmentCreateVals maps payload to ir.attachment create values", () => {
    const payload = buildSignatureAdoptionPayload({
        method: "draw",
        displayName: "Alice",
        signatureImage: VALID_SIGNATURE_DATA_URL,
    });
    expect(payload.valid).toBe(true);

    const attachmentVals = buildSignatureAttachmentCreateVals(payload.value, {
        attachmentNamePrefix: "open_sign_signature",
        attachmentResModel: "open.sign.request.value",
        attachmentResId: 99,
        companyId: 2,
    });
    expect(attachmentVals.valid).toBe(true);
    expect(attachmentVals.values.mimetype).toBe("image/png");
    expect(typeof attachmentVals.values.datas).toBe("string");
    expect(attachmentVals.values.datas.length > 0).toBe(true);
    expect(attachmentVals.values.res_model).toBe("open.sign.request.value");
    expect(attachmentVals.values.res_id).toBe(99);
    expect(attachmentVals.values.company_id).toBe(2);
});

test("createSignedPayloadAttachment creates attachment with cleaned context", async () => {
    const payload = buildSignatureAdoptionPayload({
        method: "upload",
        displayName: "Alice",
        signatureImage: VALID_SIGNATURE_DATA_URL,
    });
    const calls = [];
    const orm = {
        async create(model, valuesList, options = {}) {
            calls.push({ model, valuesList, options });
            return [42];
        },
    };

    const result = await createSignedPayloadAttachment(orm, payload.value, {
        attachmentContext: {
            lang: "en_US",
            default_template_id: 10,
        },
    });
    expect(result.valid).toBe(true);
    expect(result.errorCode).toBe(null);
    expect(result.attachmentId).toBe(42);
    expect(result.mimeType).toBe("image/png");
    expect(result.byteSize > 0).toBe(true);
    expect(calls.length).toBe(1);
    expect(calls[0].model).toBe("ir.attachment");
    expect(Boolean(calls[0].options.context.default_template_id)).toBe(false);
    expect(calls[0].options.context.lang).toBe("en_US");
});

test("createSignedPayloadAttachment returns deterministic failure codes", async () => {
    const payload = buildSignatureAdoptionPayload({
        method: "draw",
        displayName: "Alice",
        signatureImage: "not-a-data-url",
    });
    expect(payload.valid).toBe(false);

    const invalidInput = await createSignedPayloadAttachment(
        { create: async () => [1] },
        { method: "draw", signature_image: "not-a-data-url" }
    );
    expect(invalidInput).toEqual({
        valid: false,
        errorCode: "invalid_signature_image_data_url",
    });

    const badOrm = await createSignedPayloadAttachment(null, {
        method: "draw",
        signature_image: VALID_SIGNATURE_DATA_URL,
    });
    expect(badOrm).toEqual({
        valid: false,
        errorCode: "attachment_create_failed",
    });
});
