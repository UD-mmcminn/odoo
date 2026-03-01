/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { Component, onWillUnmount, useExternalListener, useRef, useState } from "@odoo/owl";

const MIN_FIELD_SIZE = 0.02;
const DEFAULT_PAGE_SIZE = Object.freeze({ width: 800, height: 1132 });

function asNumber(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

function roundGeometryNumber(value) {
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

function coerceRenderableGeometry(geometry = {}) {
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

export function applyMoveDelta(baseGeometry = {}, deltaXRatio = 0, deltaYRatio = 0) {
    const geometry = coerceRenderableGeometry(baseGeometry);
    return {
        ...geometry,
        x: roundGeometryNumber(clamp(geometry.x + deltaXRatio, 0, 1 - geometry.width)),
        y: roundGeometryNumber(clamp(geometry.y + deltaYRatio, 0, 1 - geometry.height)),
    };
}

export function applyResizeDelta(baseGeometry = {}, deltaXRatio = 0, deltaYRatio = 0) {
    const geometry = coerceRenderableGeometry(baseGeometry);
    const maxWidth = Math.max(MIN_FIELD_SIZE, 1 - geometry.x);
    const maxHeight = Math.max(MIN_FIELD_SIZE, 1 - geometry.y);

    return {
        ...geometry,
        width: roundGeometryNumber(clamp(geometry.width + deltaXRatio, MIN_FIELD_SIZE, maxWidth)),
        height: roundGeometryNumber(clamp(geometry.height + deltaYRatio, MIN_FIELD_SIZE, maxHeight)),
    };
}

function buildFieldRecord(id, page) {
    return {
        id,
        label: `Field ${id}`,
        ...coerceRenderableGeometry({
            page,
            x: 0.35,
            y: 0.2 + (id % 4) * 0.08,
            width: 0.25,
            height: 0.08,
        }),
    };
}

export class TemplateCanvas extends Component {
    static template = "open_sign_web.TemplateCanvas";
    static props = { ...standardActionServiceProps };

    setup() {
        this.pageRef = useRef("page");
        this.state = useState({
            activePage: 1,
            nextId: 2,
            pageSize: { ...DEFAULT_PAGE_SIZE },
            fields: [buildFieldRecord(1, 1)],
            interaction: null,
        });

        useExternalListener(window, "pointermove", this.onPointerMove);
        useExternalListener(window, "pointerup", this.onPointerUp);
        useExternalListener(window, "pointercancel", this.onPointerUp);
        onWillUnmount(() => {
            document.body.classList.remove("o_open_sign_web_unselectable");
        });
    }

    get pageStyle() {
        return `aspect-ratio: ${this.state.pageSize.width} / ${this.state.pageSize.height};`;
    }

    addField() {
        const fieldId = this.state.nextId;
        this.state.nextId += 1;
        this.state.fields.push(buildFieldRecord(fieldId, this.state.activePage));
    }

    isFieldActive(field) {
        return this.state.interaction && this.state.interaction.fieldId === field.id;
    }

    describeField(field) {
        const geometry = coerceRenderableGeometry(field);
        const x = Math.round(geometry.x * 100);
        const y = Math.round(geometry.y * 100);
        const width = Math.round(geometry.width * 100);
        const height = Math.round(geometry.height * 100);
        return `p${geometry.page} | x:${x}% y:${y}% w:${width}% h:${height}%`;
    }

    getFieldStyle(field) {
        const geometry = coerceRenderableGeometry(field);
        return `left:${geometry.x * 100}%;top:${geometry.y * 100}%;width:${geometry.width * 100}%;height:${geometry.height * 100}%;`;
    }

    onFieldPointerDown(field, ev) {
        if (ev.pointerType === "mouse" && ev.button !== 0) {
            return;
        }
        ev.preventDefault();
        this._startInteraction("move", field, ev);
    }

    onResizePointerDown(field, ev) {
        if (ev.pointerType === "mouse" && ev.button !== 0) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this._startInteraction("resize", field, ev);
    }

    onPointerMove(ev) {
        const interaction = this.state.interaction;
        if (!interaction) {
            return;
        }

        const field = this.state.fields.find((candidate) => candidate.id === interaction.fieldId);
        if (!field) {
            return;
        }

        const pageWidth = Math.max(1, interaction.pageWidth);
        const pageHeight = Math.max(1, interaction.pageHeight);
        const deltaXRatio = (ev.clientX - interaction.startX) / pageWidth;
        const deltaYRatio = (ev.clientY - interaction.startY) / pageHeight;
        const nextGeometry =
            interaction.type === "resize"
                ? applyResizeDelta(interaction.fieldOrigin, deltaXRatio, deltaYRatio)
                : applyMoveDelta(interaction.fieldOrigin, deltaXRatio, deltaYRatio);
        Object.assign(field, nextGeometry);
    }

    onPointerUp() {
        if (!this.state.interaction) {
            return;
        }
        this.state.interaction = null;
        document.body.classList.remove("o_open_sign_web_unselectable");
    }

    _startInteraction(type, field, ev) {
        const pageRect = this.pageRef.el && this.pageRef.el.getBoundingClientRect();
        if (!pageRect || !pageRect.width || !pageRect.height) {
            return;
        }

        this.state.interaction = {
            type,
            fieldId: field.id,
            fieldOrigin: coerceRenderableGeometry(field),
            startX: ev.clientX,
            startY: ev.clientY,
            pageWidth: pageRect.width,
            pageHeight: pageRect.height,
        };
        document.body.classList.add("o_open_sign_web_unselectable");
    }
}

registry.category("actions").add("open_sign_web.template_canvas_action", TemplateCanvas);
