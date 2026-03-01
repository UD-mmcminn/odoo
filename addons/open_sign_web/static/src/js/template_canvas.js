/** @odoo-module **/

function asNumber(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

export function serializeFieldGeometry(geometry = {}) {
    const page = Math.max(1, Math.trunc(asNumber(geometry.page, 1)));
    const x = Math.max(0, asNumber(geometry.x));
    const y = Math.max(0, asNumber(geometry.y));
    const width = Math.max(0, asNumber(geometry.width));
    const height = Math.max(0, asNumber(geometry.height));
    return { page, x, y, width, height };
}

export function normalizeCanvasToPdfCoordinates(
    geometry = {},
    canvasSize = {},
    pdfSize = {}
) {
    const normalized = serializeFieldGeometry(geometry);
    const canvasWidth = Math.max(1, asNumber(canvasSize.width, 1));
    const canvasHeight = Math.max(1, asNumber(canvasSize.height, 1));
    const pdfWidth = Math.max(1, asNumber(pdfSize.width, canvasWidth));
    const pdfHeight = Math.max(1, asNumber(pdfSize.height, canvasHeight));

    const xRatio = pdfWidth / canvasWidth;
    const yRatio = pdfHeight / canvasHeight;

    return {
        page: normalized.page,
        x: clamp(normalized.x * xRatio, 0, pdfWidth),
        y: clamp(normalized.y * yRatio, 0, pdfHeight),
        width: clamp(normalized.width * xRatio, 0, pdfWidth),
        height: clamp(normalized.height * yRatio, 0, pdfHeight),
    };
}
