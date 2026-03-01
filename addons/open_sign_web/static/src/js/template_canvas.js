/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import {
    getFieldPaletteEntries,
    getPaletteEntryByType,
} from "@open_sign_web/js/field_palette";
import {
    normalizeFieldProperties,
    sanitizeFieldLabel,
    supportsFieldOptions,
    supportsLengthBounds,
    toTemplateFieldVals,
} from "@open_sign_web/js/field_properties_panel";

import { Component, onWillUnmount, useExternalListener, useRef, useState } from "@odoo/owl";

const MIN_FIELD_SIZE = 0.02;
const DEFAULT_PAGE_SIZE = Object.freeze({ width: 800, height: 1132 });
const DEFAULT_FIELD_TYPE = "text";
const DEFAULT_OPTION_LIST = `${_t("Option 1")}\n${_t("Option 2")}`;

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

export function normalizeCanvasToPdfCoordinates(geometry = {}, canvasSize = {}, pdfSize = {}) {
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

function buildFieldRecord(id, page, fieldType, sequence) {
    const paletteEntry = getPaletteEntryByType(fieldType || DEFAULT_FIELD_TYPE);
    const properties = normalizeFieldProperties({ sequence }, paletteEntry.type);
    if (supportsFieldOptions(paletteEntry.type) && !properties.optionList) {
        properties.optionList = DEFAULT_OPTION_LIST;
    }

    return {
        id,
        type: paletteEntry.type,
        label: `${paletteEntry.label} ${id}`,
        ...properties,
        ...coerceRenderableGeometry({
            page,
            x: 0.18 + (id % 4) * 0.07,
            y: 0.16 + (id % 5) * 0.09,
            width: paletteEntry.defaultWidth,
            height: paletteEntry.defaultHeight,
        }),
    };
}

export function serializeTemplateFieldsForBackend(fields = []) {
    const normalizedFields = Array.isArray(fields) ? fields : [];
    return normalizedFields.map((field) => {
        const geometry = coerceRenderableGeometry(field);
        return {
            ...toTemplateFieldVals(field),
            page: geometry.page,
            x: geometry.x,
            y: geometry.y,
            width: geometry.width,
            height: geometry.height,
        };
    });
}

export class TemplateCanvas extends Component {
    static template = "open_sign_web.TemplateCanvas";
    static props = { ...standardActionServiceProps };

    setup() {
        this.pageRef = useRef("page");
        this.paletteEntries = getFieldPaletteEntries();
        this.paletteByType = new Map(this.paletteEntries.map((entry) => [entry.type, entry]));

        const firstField = buildFieldRecord(1, 1, DEFAULT_FIELD_TYPE, 10);
        this.state = useState({
            activePage: 1,
            nextId: 2,
            pageSize: { ...DEFAULT_PAGE_SIZE },
            fields: [firstField],
            selectedFieldId: firstField.id,
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

    get fieldPaletteEntries() {
        return this.paletteEntries;
    }

    get selectedField() {
        return this.state.fields.find((field) => field.id === this.state.selectedFieldId) || null;
    }

    get selectedFieldSupportsOptions() {
        return this.selectedField ? supportsFieldOptions(this.selectedField.type) : false;
    }

    get selectedFieldSupportsLengthBounds() {
        return this.selectedField ? supportsLengthBounds(this.selectedField.type) : false;
    }

    get backendFieldPayload() {
        return serializeTemplateFieldsForBackend(this.state.fields);
    }

    getPaletteLabel(fieldType) {
        const entry = this.paletteByType.get(fieldType);
        return entry ? entry.label : getPaletteEntryByType(DEFAULT_FIELD_TYPE).label;
    }

    addField(fieldType = DEFAULT_FIELD_TYPE) {
        const fieldId = this.state.nextId;
        this.state.nextId += 1;
        const field = buildFieldRecord(fieldId, this.state.activePage, fieldType, fieldId * 10);
        this.state.fields.push(field);
        this.state.selectedFieldId = field.id;
    }

    addFieldFromPalette(fieldType) {
        this.addField(fieldType);
    }

    removeSelectedField() {
        const selectedField = this.selectedField;
        if (!selectedField) {
            return;
        }

        this.state.fields = this.state.fields.filter((field) => field.id !== selectedField.id);
        this.state.selectedFieldId = this.state.fields[0] ? this.state.fields[0].id : null;
        this.state.interaction = null;
    }

    selectField(fieldId) {
        this.state.selectedFieldId = fieldId;
    }

    isFieldSelected(field) {
        return this.state.selectedFieldId === field.id;
    }

    isFieldActive(field) {
        return this.state.interaction && this.state.interaction.fieldId === field.id;
    }

    getFieldClasses(field) {
        const classes = [];
        if (this.isFieldSelected(field)) {
            classes.push("o_is_selected");
        }
        if (this.isFieldActive(field)) {
            classes.push("o_is_active");
        }
        return classes.join(" ");
    }

    describeField(field) {
        const geometry = coerceRenderableGeometry(field);
        const x = Math.round(geometry.x * 100);
        const y = Math.round(geometry.y * 100);
        const width = Math.round(geometry.width * 100);
        const height = Math.round(geometry.height * 100);
        return `${this.getPaletteLabel(field.type)} | p${geometry.page} | x:${x}% y:${y}% w:${width}% h:${height}%`;
    }

    getFieldStyle(field) {
        const geometry = coerceRenderableGeometry(field);
        return `left:${geometry.x * 100}%;top:${geometry.y * 100}%;width:${geometry.width * 100}%;height:${geometry.height * 100}%;`;
    }

    updateSelectedFieldLabel(ev) {
        this._updateSelectedFieldProperties({ label: ev.target.value });
    }

    updateSelectedFieldType(ev) {
        this._updateSelectedFieldProperties({ type: ev.target.value });
    }

    updateSelectedFieldRequired(ev) {
        this._updateSelectedFieldProperties({ required: ev.target.checked });
    }

    updateSelectedFieldSequence(ev) {
        this._updateSelectedFieldProperties({ sequence: ev.target.value });
    }

    updateSelectedFieldPlaceholder(ev) {
        this._updateSelectedFieldProperties({ placeholder: ev.target.value });
    }

    updateSelectedFieldHelpText(ev) {
        this._updateSelectedFieldProperties({ helpText: ev.target.value });
    }

    updateSelectedFieldDefaultValue(ev) {
        this._updateSelectedFieldProperties({ defaultValue: ev.target.value });
    }

    updateSelectedFieldValidationRegex(ev) {
        this._updateSelectedFieldProperties({ validationRegex: ev.target.value });
    }

    updateSelectedFieldMinLength(ev) {
        this._updateSelectedFieldProperties({ minLength: ev.target.value });
    }

    updateSelectedFieldMaxLength(ev) {
        this._updateSelectedFieldProperties({ maxLength: ev.target.value });
    }

    updateSelectedFieldOptionList(ev) {
        this._updateSelectedFieldProperties({ optionList: ev.target.value });
    }

    onFieldPointerDown(field, ev) {
        if (ev.pointerType === "mouse" && ev.button !== 0) {
            return;
        }
        ev.preventDefault();
        this.selectField(field.id);
        this._startInteraction("move", field, ev);
    }

    onResizePointerDown(field, ev) {
        if (ev.pointerType === "mouse" && ev.button !== 0) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.selectField(field.id);
        this._startInteraction("resize", field, ev);
    }

    onCanvasPointerDown() {
        this.state.selectedFieldId = null;
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

    _updateSelectedFieldProperties(patch = {}) {
        const field = this.selectedField;
        if (!field) {
            return;
        }

        const nextType = patch.type || field.type;
        const nextValues = { ...field, ...patch };
        const normalized = normalizeFieldProperties(nextValues, nextType);
        if (supportsFieldOptions(nextType) && !normalized.optionList) {
            normalized.optionList = DEFAULT_OPTION_LIST;
        }

        Object.assign(field, {
            type: nextType,
            label: sanitizeFieldLabel(nextValues.label, `${this.getPaletteLabel(nextType)} ${field.id}`),
            required: normalized.required,
            sequence: normalized.sequence,
            placeholder: normalized.placeholder,
            helpText: normalized.helpText,
            defaultValue: normalized.defaultValue,
            validationRegex: normalized.validationRegex,
            minLength: normalized.minLength,
            maxLength: normalized.maxLength,
            optionList: normalized.optionList,
        });
    }
}

registry.category("actions").add("open_sign_web.template_canvas_action", TemplateCanvas);
