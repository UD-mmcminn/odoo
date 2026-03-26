/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import {
    DEFAULT_PAGE_SIZE,
    MIN_FIELD_SIZE,
    asNumber,
    clamp,
    coerceRenderableGeometry,
    formatOverlayFieldStyle,
    formatPdfPageStyle,
    loadPdfPagesFromUrl,
    roundGeometryNumber,
    serializeFieldGeometry,
} from "@open_sign_web/js/pdf_surface_utils";
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
import { openSignatureAdoptionDialog } from "@open_sign_web/js/signature_adoption_dialog";

import {
    Component,
    onWillStart,
    onWillUnmount,
    useExternalListener,
    useState,
} from "@odoo/owl";

const DEFAULT_FIELD_TYPE = "text";
const TEMPLATE_MODEL = "open.sign.template";
const ROLE_MODEL = "open.sign.role";
const TEMPLATE_FIELD_MODEL = "open.sign.template.field";
const TEMPLATE_FIELD_OPTION_MODEL = "open.sign.template.field.option";
const ROLE_REQUIRED_LABEL = _t("Role required");
const INVALID_ROLE_LABEL = _t("Invalid role");
const SIGNATURE_ADOPTION_FIELD_TYPES = new Set(["signature", "stamp"]);
const DEFAULT_SIGNATURE_DISPLAY_NAME = _t("Signer");

function getDefaultOptionList() {
    return `${_t("Option 1")}\n${_t("Option 2")}`;
}

function asPositiveInteger(value) {
    const parsed = Number.parseInt(value, 10);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function cleanContextDefaults(context = {}) {
    const baseContext = context && typeof context === "object" ? context : {};
    return Object.fromEntries(
        Object.entries(baseContext).filter(([key]) => !String(key).startsWith("default_"))
    );
}

function normalizeRoleIdSet(availableRoleIds = []) {
    if (availableRoleIds instanceof Set) {
        return new Set([...availableRoleIds].map((value) => asPositiveInteger(value)).filter(Boolean));
    }
    const normalizedItems = Array.isArray(availableRoleIds) ? availableRoleIds : [];
    const roleIds = normalizedItems
        .map((item) => asPositiveInteger(item && typeof item === "object" ? item.id : item))
        .filter(Boolean);
    return new Set(roleIds);
}

export function isFieldRoleValid(field = {}, availableRoleIds = []) {
    const roleId = asPositiveInteger(field.roleId ?? field.role_id);
    if (!roleId) {
        return false;
    }
    const roleIdSet = normalizeRoleIdSet(availableRoleIds);
    return roleIdSet.has(roleId);
}

export function countInvalidFieldRoles(fields = [], availableRoleIds = []) {
    const normalizedFields = Array.isArray(fields) ? fields : [];
    const roleIdSet = normalizeRoleIdSet(availableRoleIds);
    let invalidCount = 0;
    for (const field of normalizedFields) {
        const roleId = asPositiveInteger(field.roleId ?? field.role_id);
        if (!roleId || !roleIdSet.has(roleId)) {
            invalidCount += 1;
        }
    }
    return invalidCount;
}

export function supportsSignatureAdoption(fieldType) {
    return SIGNATURE_ADOPTION_FIELD_TYPES.has(fieldType);
}

export { serializeFieldGeometry };

export function normalizePageNumber(pageNumber, pages = [], fallback = 1) {
    const normalizedFallback = Math.max(1, Math.trunc(asNumber(fallback, 1)));
    const pageCandidate =
        pageNumber === null || pageNumber === undefined || pageNumber === ""
            ? normalizedFallback
            : pageNumber;
    const normalizedPageNumber = Math.max(
        1,
        Math.trunc(asNumber(pageCandidate, normalizedFallback))
    );
    const normalizedPages = (Array.isArray(pages) ? pages : [])
        .map((page) => Math.max(1, Math.trunc(asNumber(page?.number ?? page, normalizedFallback))))
        .filter((value, index, values) => values.indexOf(value) === index)
        .sort((left, right) => left - right);
    if (!normalizedPages.length) {
        return normalizedPageNumber;
    }
    return normalizedPages.includes(normalizedPageNumber) ? normalizedPageNumber : normalizedPages[0];
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

function buildFieldRecord(id, page, fieldType, sequence, roleId = null) {
    const paletteEntry = getPaletteEntryByType(fieldType || DEFAULT_FIELD_TYPE);
    const properties = normalizeFieldProperties({ sequence }, paletteEntry.type);
    if (supportsFieldOptions(paletteEntry.type) && !properties.optionList) {
        properties.optionList = getDefaultOptionList();
    }

    return {
        id,
        roleId,
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

export function serializeTemplateFieldsForBackend(fields = [], options = {}) {
    const normalizedFields = Array.isArray(fields) ? fields : [];
    const roleIdSet = normalizeRoleIdSet(options.availableRoleIds || []);
    const requireValidRoles = Boolean(options.requireValidRoles);
    return normalizedFields.map((field) => {
        if (requireValidRoles && !isFieldRoleValid(field, roleIdSet)) {
            throw new Error("Template field role assignment is invalid for the selected template.");
        }
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
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.onPointerMove = this.onPointerMove.bind(this);
        this.onPointerUp = this.onPointerUp.bind(this);
        this.onCanvasPointerDown = this.onCanvasPointerDown.bind(this);
        this.onFieldPointerDown = this.onFieldPointerDown.bind(this);
        this.onResizePointerDown = this.onResizePointerDown.bind(this);
        this._roleOptionsLoadToken = 0;
        this._templateFieldLoadToken = 0;
        this._pdfLoadToken = 0;
        this.paletteEntries = getFieldPaletteEntries();
        this.paletteByType = new Map(this.paletteEntries.map((entry) => [entry.type, entry]));
        const actionContext = this.props.action?.context || {};
        const contextTemplateId =
            actionContext.active_model === TEMPLATE_MODEL
                ? asPositiveInteger(actionContext.active_id)
                : null;

        this.state = useState({
            activePage: 1,
            nextId: 1,
            templateId: contextTemplateId,
            templateOptions: [],
            roleOptions: [],
            pageSize: { ...DEFAULT_PAGE_SIZE },
            fields: [],
            selectedFieldId: null,
            interaction: null,
            isDirty: false,
            isSaving: false,
            pdfPages: [],
        });

        onWillStart(async () => {
            await this._loadTemplateOptions();
            if (!this.state.templateId && this.state.templateOptions.length) {
                this.state.templateId = this.state.templateOptions[0].id;
            }
            await this._loadRoleOptions();
            await this._loadTemplatePdfPages();
            await this._loadTemplateFields();
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

    get canvasPages() {
        if (this.state.pdfPages.length) {
            return this.state.pdfPages;
        }
        return [
            {
                number: 1,
                width: this.state.pageSize.width,
                height: this.state.pageSize.height,
                imageDataUrl: null,
            },
        ];
    }

    get fieldPaletteEntries() {
        return this.paletteEntries;
    }

    get totalPageCount() {
        return this.canvasPages.length;
    }

    get templateOptions() {
        return this.state.templateOptions;
    }

    get roleOptions() {
        return this.state.roleOptions;
    }

    get canAddFields() {
        return Boolean(this.state.templateId) && this.state.roleOptions.length > 0;
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

    get selectedFieldSupportsSignatureAdoption() {
        return this.selectedField ? supportsSignatureAdoption(this.selectedField.type) : false;
    }

    get selectedFieldRoleValid() {
        if (!this.selectedField) {
            return true;
        }
        return isFieldRoleValid(this.selectedField, this.state.roleOptions);
    }

    get defaultRoleId() {
        return this.state.roleOptions[0] ? this.state.roleOptions[0].id : null;
    }

    get invalidRoleFieldCount() {
        return countInvalidFieldRoles(this.state.fields, this.state.roleOptions);
    }

    get hasInvalidRoleAssignments() {
        return this.invalidRoleFieldCount > 0;
    }

    get canSerializeBackendPayload() {
        return Boolean(this.state.templateId) && !this.hasInvalidRoleAssignments;
    }

    get canSaveFields() {
        return this.canSerializeBackendPayload && this.state.isDirty && !this.state.isSaving;
    }

    get backendFieldPayload() {
        if (!this.canSerializeBackendPayload) {
            return null;
        }
        return serializeTemplateFieldsForBackend(this.state.fields, {
            requireValidRoles: true,
            availableRoleIds: this.state.roleOptions,
        });
    }

    getPaletteLabel(fieldType) {
        const entry = this.paletteByType.get(fieldType);
        return entry ? entry.label : getPaletteEntryByType(DEFAULT_FIELD_TYPE).label;
    }

    getRoleLabel(roleId) {
        const normalizedRoleId = asPositiveInteger(roleId);
        if (!normalizedRoleId) {
            return ROLE_REQUIRED_LABEL;
        }
        const role = this.state.roleOptions.find((candidate) => candidate.id === normalizedRoleId);
        return role ? role.name : INVALID_ROLE_LABEL;
    }

    addField(fieldType = DEFAULT_FIELD_TYPE) {
        if (!this.canAddFields) {
            return;
        }
        const activePage = normalizePageNumber(this.state.activePage, this.canvasPages, 1);
        this.state.activePage = activePage;
        const fieldId = this.state.nextId;
        this.state.nextId += 1;
        const field = buildFieldRecord(
            fieldId,
            activePage,
            fieldType,
            fieldId * 10,
            this.defaultRoleId
        );
        field.backendId = null;
        field.backendType = null;
        field.backendOptionList = "";
        field.backendHadOptions = false;
        this.state.fields.push(field);
        this.state.selectedFieldId = field.id;
        this.state.isDirty = true;
    }

    addFieldFromPalette(fieldType) {
        this.addField(fieldType);
    }

    async onTemplateChange(ev) {
        this.state.templateId = asPositiveInteger(ev.target.value);
        this.state.fields = [];
        this.state.selectedFieldId = null;
        this.state.interaction = null;
        this.state.nextId = 1;
        this.state.roleOptions = [];
        this.state.isDirty = false;
        this.state.pdfPages = [];
        this.state.activePage = 1;
        await this._loadRoleOptions();
        await this._loadTemplatePdfPages();
        await this._loadTemplateFields();
    }

    removeSelectedField() {
        const selectedField = this.selectedField;
        if (!selectedField) {
            return;
        }

        this.state.fields = this.state.fields.filter((field) => field.id !== selectedField.id);
        this.state.selectedFieldId = this.state.fields[0] ? this.state.fields[0].id : null;
        this.state.interaction = null;
        this.state.isDirty = true;
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
        const roleLabel = this.getRoleLabel(field.roleId);
        const x = Math.round(geometry.x * 100);
        const y = Math.round(geometry.y * 100);
        const width = Math.round(geometry.width * 100);
        const height = Math.round(geometry.height * 100);
        return `${this.getPaletteLabel(field.type)} | ${roleLabel} | p${geometry.page} | x:${x}% y:${y}% w:${width}% h:${height}%`;
    }

    getFieldStyle(field) {
        return formatOverlayFieldStyle(field);
    }

    getPageStyle(page) {
        return formatPdfPageStyle(page, this.state.pageSize);
    }

    getFieldsForPage(pageNumber) {
        const normalizedPageNumber = Math.max(1, Math.trunc(asNumber(pageNumber, 1)));
        return this.state.fields.filter(
            (field) => serializeFieldGeometry(field).page === normalizedPageNumber
        );
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

    updateSelectedFieldRole(ev) {
        this._updateSelectedFieldProperties({ roleId: asPositiveInteger(ev.target.value) });
    }

    openSelectedFieldSignatureDialog() {
        const selectedField = this.selectedField;
        if (!selectedField || !this.selectedFieldSupportsSignatureAdoption) {
            return;
        }
        const defaultMethod = selectedField.signatureAdoptionPayload?.method || "draw";
        const defaultName =
            selectedField.signatureAdoptionPayload?.display_name ||
            selectedField.signatureAdoptionPayload?.displayName ||
            DEFAULT_SIGNATURE_DISPLAY_NAME;
        openSignatureAdoptionDialog(this.dialog, {
            defaultMethod,
            defaultName,
            attachmentResModel: "open.sign.request.value",
            attachmentNamePrefix:
                selectedField.type === "stamp" ? "open_sign_stamp" : "open_sign_signature",
            attachmentContext: cleanContextDefaults(this.props.action?.context || {}),
            adoptSignature: async (payload) => {
                this._applySignatureAdoptionPayload(selectedField.id, payload);
            },
        });
    }

    _applySignatureAdoptionPayload(fieldId, payload) {
        const targetField = this.state.fields.find((field) => field.id === fieldId);
        if (!targetField || !payload) {
            return;
        }
        targetField.signatureAdoptionPayload = {
            method: payload.method || "draw",
            display_name: payload.display_name || "",
            signed_payload_attachment_id: asPositiveInteger(payload.signed_payload_attachment_id),
            signature_image_mime_type: payload.signature_image_mime_type || "",
            signature_image_byte_size: Number.parseInt(payload.signature_image_byte_size, 10) || 0,
        };
        this.state.isDirty = true;
    }

    async saveTemplateFields() {
        if (!this.canSaveFields) {
            return;
        }
        this.state.isSaving = true;
        try {
            const selectedTemplateId = this.state.templateId;
            const persistedFieldRows = await this.orm.searchRead(
                TEMPLATE_FIELD_MODEL,
                [["template_id", "=", selectedTemplateId]],
                ["id"],
                { order: "id" }
            );
            const existingBackendFieldIds = new Set(
                persistedFieldRows.map((row) => asPositiveInteger(row.id)).filter(Boolean)
            );
            const retainedBackendFieldIds = new Set();

            for (const field of this.state.fields) {
                const fieldVals = this._serializeFieldForBackendWrite(field);
                if (field.backendId) {
                    await this.orm.write(TEMPLATE_FIELD_MODEL, [field.backendId], fieldVals);
                    retainedBackendFieldIds.add(field.backendId);
                } else {
                    const [createdFieldId] = await this.orm.create(TEMPLATE_FIELD_MODEL, [
                        {
                            ...fieldVals,
                            template_id: selectedTemplateId,
                        },
                    ]);
                    const previousFieldId = field.id;
                    field.id = createdFieldId;
                    field.backendId = createdFieldId;
                    if (this.state.selectedFieldId === previousFieldId) {
                        this.state.selectedFieldId = createdFieldId;
                    }
                    retainedBackendFieldIds.add(createdFieldId);
                }
                field.backendType = field.type;
                field.backendOptionList = field.optionList;
                field.backendHadOptions = supportsFieldOptions(field.type) && Boolean(field.optionList);
            }

            const removedFieldIds = [...existingBackendFieldIds].filter(
                (fieldId) => !retainedBackendFieldIds.has(fieldId)
            );
            if (removedFieldIds.length) {
                await this.orm.unlink(TEMPLATE_FIELD_MODEL, removedFieldIds);
            }

            this.state.nextId = this._computeNextFieldId(this.state.fields);
            this.state.isDirty = false;
            this.notification.add(_t("Template fields saved."), { type: "success" });
        } catch (error) {
            this.notification.add(
                _t("Unable to save template fields. Review values and try again."),
                { type: "danger" }
            );
            throw error;
        } finally {
            this.state.isSaving = false;
        }
    }

    onFieldPointerDown(field, ev) {
        if (ev.pointerType === "mouse" && ev.button !== 0) {
            return;
        }
        ev.preventDefault();
        this.state.activePage = normalizePageNumber(field.page, this.canvasPages, this.state.activePage);
        this.selectField(field.id);
        this._startInteraction("move", field, ev);
    }

    onResizePointerDown(field, ev) {
        if (ev.pointerType === "mouse" && ev.button !== 0) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.state.activePage = normalizePageNumber(field.page, this.canvasPages, this.state.activePage);
        this.selectField(field.id);
        this._startInteraction("resize", field, ev);
    }

    onCanvasPointerDown() {
        this.state.selectedFieldId = null;
    }

    onCanvasPagePointerDown(pageNumber, ev) {
        if (ev?.target?.closest?.(".o_open_sign_web_field")) {
            return;
        }
        this.state.activePage = normalizePageNumber(pageNumber, this.canvasPages, this.state.activePage);
        this.state.selectedFieldId = null;
    }

    goToPreviousPage() {
        const pageNumbers = this.canvasPages
            .map((page) => Math.max(1, Math.trunc(asNumber(page.number, 1))))
            .sort((left, right) => left - right);
        const currentIndex = pageNumbers.indexOf(
            normalizePageNumber(this.state.activePage, pageNumbers, 1)
        );
        if (currentIndex > 0) {
            this.state.activePage = pageNumbers[currentIndex - 1];
            this.state.selectedFieldId = null;
        }
    }

    goToNextPage() {
        const pageNumbers = this.canvasPages
            .map((page) => Math.max(1, Math.trunc(asNumber(page.number, 1))))
            .sort((left, right) => left - right);
        const currentIndex = pageNumbers.indexOf(
            normalizePageNumber(this.state.activePage, pageNumbers, 1)
        );
        if (currentIndex !== -1 && currentIndex < pageNumbers.length - 1) {
            this.state.activePage = pageNumbers[currentIndex + 1];
            this.state.selectedFieldId = null;
        }
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
        this.state.isDirty = true;
    }

    _startInteraction(type, field, ev) {
        const pageElement = ev.target.closest(".o_open_sign_web_canvas_page");
        const pageRect = pageElement && pageElement.getBoundingClientRect();
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

    async _loadTemplateOptions() {
        this.state.templateOptions = await this.orm.searchRead(TEMPLATE_MODEL, [], ["id", "name"], {
            order: "name, id",
        });
    }

    async _loadRoleOptions() {
        const loadToken = ++this._roleOptionsLoadToken;
        const selectedTemplateId = this.state.templateId;
        if (!selectedTemplateId) {
            this.state.roleOptions = [];
            return;
        }
        const roleOptions = await this.orm.searchRead(
            ROLE_MODEL,
            [["template_id", "=", selectedTemplateId]],
            ["id", "name", "sequence"],
            { order: "sequence, id" }
        );
        if (loadToken !== this._roleOptionsLoadToken) {
            return;
        }
        this.state.roleOptions = roleOptions;
    }

    async _loadTemplatePdfPages() {
        const loadToken = ++this._pdfLoadToken;
        const selectedTemplateId = this.state.templateId;
        if (!selectedTemplateId) {
            this.state.pdfPages = [];
            this.state.activePage = 1;
            this.state.pageSize = { ...DEFAULT_PAGE_SIZE };
            return;
        }

        const [template] = await this.orm.searchRead(
            TEMPLATE_MODEL,
            [["id", "=", selectedTemplateId]],
            ["source_attachment_id"],
            { limit: 1 }
        );
        if (loadToken !== this._pdfLoadToken) {
            return;
        }
        const attachmentId = this._extractMany2OneId(template?.source_attachment_id);
        if (!attachmentId) {
            this.state.pdfPages = [];
            this.state.activePage = 1;
            this.state.pageSize = { ...DEFAULT_PAGE_SIZE };
            return;
        }

        const pdfUrl = url(`/web/content/${attachmentId}`);
        try {
            const pages = await loadPdfPagesFromUrl(pdfUrl);
            if (loadToken !== this._pdfLoadToken) {
                return;
            }
            this.state.pdfPages = pages;
            if (pages[0]) {
                this.state.pageSize = { width: pages[0].width, height: pages[0].height };
            } else {
                this.state.pageSize = { ...DEFAULT_PAGE_SIZE };
            }
            this.state.activePage = normalizePageNumber(this.state.activePage, pages, 1);
        } catch (_error) {
            if (loadToken !== this._pdfLoadToken) {
                return;
            }
            this.state.pdfPages = [];
            this.state.activePage = 1;
            this.state.pageSize = { ...DEFAULT_PAGE_SIZE };
            this.notification.add(_t("Could not display the selected pdf"), { type: "danger" });
        }
    }

    async _loadTemplateFields() {
        const loadToken = ++this._templateFieldLoadToken;
        const selectedTemplateId = this.state.templateId;
        if (!selectedTemplateId) {
            this.state.fields = [];
            this.state.selectedFieldId = null;
            this.state.nextId = 1;
            this.state.isDirty = false;
            return;
        }

        const templateFields = await this.orm.searchRead(
            TEMPLATE_FIELD_MODEL,
            [["template_id", "=", selectedTemplateId]],
            [
                "id",
                "role_id",
                "type",
                "label",
                "required",
                "page",
                "x",
                "y",
                "width",
                "height",
                "sequence",
                "default_value",
                "validation_regex",
                "min_length",
                "max_length",
            ],
            { order: "page, sequence, id" }
        );
        if (loadToken !== this._templateFieldLoadToken) {
            return;
        }

        const templateFieldIds = templateFields
            .map((field) => asPositiveInteger(field.id))
            .filter(Boolean);
        const optionMapByFieldId = new Map();
        if (templateFieldIds.length) {
            const fieldOptions = await this.orm.searchRead(
                TEMPLATE_FIELD_OPTION_MODEL,
                [["field_id", "in", templateFieldIds]],
                ["id", "field_id", "value", "sequence"],
                { order: "field_id, sequence, id" }
            );
            if (loadToken !== this._templateFieldLoadToken) {
                return;
            }
            for (const option of fieldOptions) {
                const fieldId = this._extractMany2OneId(option.field_id);
                if (!fieldId) {
                    continue;
                }
                const existingOptions = optionMapByFieldId.get(fieldId) || [];
                existingOptions.push(option);
                optionMapByFieldId.set(fieldId, existingOptions);
            }
        }

        this.state.fields = templateFields.map((field) => this._toCanvasField(field, optionMapByFieldId));
        this.state.selectedFieldId = this.state.fields[0] ? this.state.fields[0].id : null;
        this.state.nextId = this._computeNextFieldId(this.state.fields);
        this.state.activePage = normalizePageNumber(this.state.activePage, this.canvasPages, 1);
        this.state.isDirty = false;
    }

    _computeNextFieldId(fields = []) {
        const maxId = fields.reduce((acc, field) => Math.max(acc, asPositiveInteger(field.id) || 0), 0);
        return maxId + 1;
    }

    _extractMany2OneId(value) {
        if (Array.isArray(value)) {
            return asPositiveInteger(value[0]);
        }
        return asPositiveInteger(value);
    }

    _toCanvasField(field, optionMapByFieldId) {
        const backendFieldId = asPositiveInteger(field.id);
        const fieldType = field.type || DEFAULT_FIELD_TYPE;
        const optionList = (optionMapByFieldId.get(backendFieldId) || [])
            .map((option) => String(option.value || "").trim())
            .filter(Boolean)
            .join("\n");
        const normalizedProperties = normalizeFieldProperties(
            {
                required: field.required,
                sequence: field.sequence,
                defaultValue: field.default_value ?? "",
                validationRegex: field.validation_regex || "",
                minLength: field.min_length,
                maxLength: field.max_length,
                optionList,
            },
            fieldType
        );
        return {
            id: backendFieldId,
            backendId: backendFieldId,
            backendType: fieldType,
            backendOptionList: normalizedProperties.optionList,
            backendHadOptions: optionList.length > 0,
            roleId: this._extractMany2OneId(field.role_id),
            type: fieldType,
            label: sanitizeFieldLabel(field.label, `${this.getPaletteLabel(fieldType)} ${backendFieldId}`),
            required: normalizedProperties.required,
            sequence: normalizedProperties.sequence,
            placeholder: "",
            helpText: "",
            defaultValue: normalizedProperties.defaultValue,
            validationRegex: normalizedProperties.validationRegex,
            minLength: normalizedProperties.minLength,
            maxLength: normalizedProperties.maxLength,
            optionList: normalizedProperties.optionList,
            ...coerceRenderableGeometry({
                page: field.page,
                x: field.x,
                y: field.y,
                width: field.width,
                height: field.height,
            }),
        };
    }

    _serializeFieldForBackendWrite(field) {
        const [fieldVals] = serializeTemplateFieldsForBackend([field], {
            requireValidRoles: true,
            availableRoleIds: this.state.roleOptions,
        });
        const backendWasOptionField = supportsFieldOptions(field.backendType);
        const backendHasId = Boolean(field.backendId);
        const optionsChanged = field.optionList !== (field.backendOptionList || "");
        const typeChanged = field.type !== field.backendType;
        if (supportsFieldOptions(field.type)) {
            if (backendHasId && (optionsChanged || typeChanged)) {
                fieldVals.option_ids = [[5, 0, 0], ...fieldVals.option_ids];
            } else if (backendHasId) {
                delete fieldVals.option_ids;
            }
        } else if (backendHasId && (field.backendHadOptions || backendWasOptionField)) {
            fieldVals.option_ids = [[5, 0, 0]];
        } else {
            delete fieldVals.option_ids;
        }
        return fieldVals;
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
            normalized.optionList = getDefaultOptionList();
        }

        Object.assign(field, {
            roleId: asPositiveInteger(nextValues.roleId),
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
        this.state.isDirty = true;
    }
}

registry.category("actions").add("open_sign_web.template_canvas_action", TemplateCanvas);
