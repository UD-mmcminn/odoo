/** @odoo-module **/

export function buildSignerPreviewContext(context = {}) {
    return {
        roleName: context.roleName || "",
        roleId: context.roleId || false,
        fields: Array.isArray(context.fields) ? context.fields : [],
    };
}
