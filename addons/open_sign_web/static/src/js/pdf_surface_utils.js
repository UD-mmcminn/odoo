/** @odoo-module **/

import { loadPDFJSAssets } from "@web/core/utils/pdfjs";

export const DEFAULT_PAGE_SIZE = Object.freeze({ width: 800, height: 1132 });
export const MIN_FIELD_SIZE = 0.02;

export function asNumber(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
}

export function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

export function roundGeometryNumber(value) {
    return Math.round(value * 10000) / 10000;
}

export function serializeFieldGeometry(geometry = {}) {
    const page = Math.max(1, Math.trunc(asNumber(geometry.page, 1)));
    const x = Math.max(0, asNumber(geometry.x));
    const y = Math.max(0, asNumber(geometry.y));
    const width = Math.max(0, asNumber(geometry.width));
    const height = Math.max(0, asNumber(geometry.height));
    return { page, x, y, width, height };
}

export function coerceRenderableGeometry(geometry = {}) {
    const normalized = serializeFieldGeometry(geometry);
    const width = clamp(normalized.width || MIN_FIELD_SIZE, MIN_FIELD_SIZE, 1);
    const height = clamp(normalized.height || MIN_FIELD_SIZE, MIN_FIELD_SIZE, 1);
    const x = clamp(normalized.x, 0, 1 - width);
    const y = clamp(normalized.y, 0, 1 - height);

    return {
        page: normalized.page,
        x: roundGeometryNumber(x),
        y: roundGeometryNumber(y),
        width: roundGeometryNumber(width),
        height: roundGeometryNumber(height),
    };
}

export function formatOverlayFieldStyle(geometry = {}) {
    const renderable = coerceRenderableGeometry(geometry);
    return `left:${renderable.x * 100}%;top:${renderable.y * 100}%;width:${renderable.width * 100}%;height:${renderable.height * 100}%;`;
}

export function formatPdfPageStyle(page = {}, fallbackSize = DEFAULT_PAGE_SIZE) {
    const width = Math.max(1, asNumber(page.width, fallbackSize.width));
    const height = Math.max(1, asNumber(page.height, fallbackSize.height));
    return `aspect-ratio: ${width} / ${height};`;
}

export async function loadPdfPagesFromUrl(pdfUrl) {
    if (!pdfUrl) {
        return [];
    }
    let initialWorkerSrc = null;
    await loadPDFJSAssets();
    initialWorkerSrc = globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc;
    globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc = "/web/static/lib/pdfjs/build/pdf.worker.js";
    try {
        const pdf = await globalThis.pdfjsLib.getDocument(pdfUrl).promise;
        const pages = [];
        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber++) {
            const page = await pdf.getPage(pageNumber);
            const baseViewport = page.getViewport({ scale: 1 });
            const renderScale = Math.max(1, Math.min(1.5, 1100 / Math.max(1, baseViewport.width)));
            const viewport = page.getViewport({ scale: renderScale });
            const canvas = document.createElement("canvas");
            canvas.width = Math.max(1, Math.floor(viewport.width));
            canvas.height = Math.max(1, Math.floor(viewport.height));
            const canvasContext = canvas.getContext("2d");
            await page.render({ canvasContext, viewport }).promise;
            pages.push({
                number: pageNumber,
                width: viewport.width,
                height: viewport.height,
                imageDataUrl: canvas.toDataURL("image/png"),
            });
        }
        return pages;
    } finally {
        if (globalThis.pdfjsLib && initialWorkerSrc !== null) {
            globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc = initialWorkerSrc;
        }
    }
}
