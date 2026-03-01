# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


SHA256_HEX_RE = re.compile(r'^[0-9a-f]{64}$')
IMMUTABLE_REQUEST_STATUSES = {'completed', 'cancelled', 'voided'}
VERSION_REQUIRED_STATUSES = {
    'versioned',
    'sent',
    'opened',
    'in_progress',
    'partially_signed',
    'completed',
    'declined',
    'expired',
    'voided',
}
ALLOWED_STATUS_TRANSITIONS = {
    'draft': {'versioned', 'cancelled'},
    'versioned': {'sent', 'cancelled'},
    'sent': {'opened', 'in_progress', 'declined', 'expired', 'cancelled'},
    'opened': {'in_progress', 'declined', 'expired', 'cancelled'},
    'in_progress': {'partially_signed', 'completed', 'declined', 'expired', 'cancelled'},
    'partially_signed': {'in_progress', 'completed', 'declined', 'expired', 'cancelled'},
    'completed': {'voided'},
    'declined': {'cancelled'},
    'expired': {'cancelled'},
    'cancelled': set(),
    'voided': set(),
}


class OpenSignRequest(models.Model):
    _name = 'open.sign.request'
    _description = 'Open Sign Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(required=True, default=lambda self: _("New Sign Request"), index=True, tracking=True)
    template_id = fields.Many2one(
        'open.sign.template',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
        tracking=True,
    )
    template_version_id = fields.Many2one(
        'open.sign.template.version',
        ondelete='restrict',
        index=True,
        check_company=True,
        tracking=True,
    )
    status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('versioned', 'Versioned'),
            ('sent', 'Sent'),
            ('opened', 'Opened'),
            ('in_progress', 'In Progress'),
            ('partially_signed', 'Partially Signed'),
            ('completed', 'Completed'),
            ('declined', 'Declined'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
            ('voided', 'Voided'),
        ],
        required=True,
        default='draft',
        index=True,
        tracking=True,
    )
    sent_at = fields.Datetime(index=True, tracking=True)
    completed_at = fields.Datetime(index=True, tracking=True)
    expires_at = fields.Datetime(index=True, tracking=True)
    final_attachment_id = fields.Many2one(
        'ir.attachment',
        ondelete='restrict',
        index=True,
        check_company=True,
        tracking=True,
    )
    source_pdf_sha256 = fields.Char(index=True, tracking=True)
    final_pdf_sha256 = fields.Char(index=True, tracking=True)
    active = fields.Boolean(default=True, index=True)
    deleted_at = fields.Datetime(index=True)
    owner_id = fields.Many2one(
        'res.users',
        required=True,
        default=lambda self: self.env.user,
        ondelete='restrict',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    ordered_signing = fields.Boolean(required=True, default=True)
    evidence_schema_version = fields.Char(required=True, default='v1', index=True)
    lock_version = fields.Integer(required=True, default=0, index=True)
    signer_ids = fields.One2many('open.sign.request.signer', 'request_id', string='Signers')
    value_ids = fields.One2many('open.sign.request.value', 'request_id', string='Values')
    audit_log_ids = fields.One2many('open.sign.audit.log', 'request_id', string='Audit Logs')
    signed_count = fields.Integer(compute='_compute_signer_counts', store=True, index=True)
    pending_count = fields.Integer(compute='_compute_signer_counts', store=True, index=True)
    declined_count = fields.Integer(compute='_compute_signer_counts', store=True, index=True)
    last_event_at = fields.Datetime(index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            status = vals.get('status', 'draft')
            if status != 'draft':
                raise ValidationError(_("Sign requests must be created in draft status."))
        return super().create(vals_list)

    @api.model
    def _can_hard_delete_request(self):
        return self.env.su and self.env.context.get('open_sign_allow_request_hard_delete')

    def _guard_terminal_request_mutation(self, vals):
        if self.env.su or not vals:
            return
        changed_fields = set(vals)
        for request in self:
            if request.status not in IMMUTABLE_REQUEST_STATUSES:
                continue
            if (
                request.status == 'completed'
                and changed_fields.issubset({'status', 'last_event_at'})
                and vals.get('status') == 'voided'
            ):
                continue
            if (
                self.env.context.get('open_sign_soft_delete')
                and changed_fields.issubset({'active', 'deleted_at'})
                and vals.get('active') is False
            ):
                continue
            raise ValidationError(_("Completed, cancelled, and voided requests are immutable and cannot be modified directly."))

    def _sanitize_retention_fields_on_write(self, vals):
        vals = dict(vals)
        if self.env.su:
            return vals

        has_active = 'active' in vals
        has_deleted_at = 'deleted_at' in vals
        if has_deleted_at and not has_active:
            raise ValidationError(_("Request deletion timestamp cannot be modified directly."))
        if not has_active:
            return vals

        target_active = vals.get('active')
        if target_active is False:
            self.check_access('unlink')
            vals['deleted_at'] = fields.Datetime.now()
        elif target_active is True:
            self.check_access('unlink')
            if any(not request.active for request in self):
                vals['deleted_at'] = False
            else:
                vals.pop('deleted_at', None)
        return vals

    def _check_binding_immutability(self, vals):
        immutable_fields = {'template_id', 'template_version_id', 'source_pdf_sha256'}
        if not immutable_fields.intersection(vals):
            return
        for request in self.filtered(lambda rec: rec.status in VERSION_REQUIRED_STATUSES):
            if 'template_id' in vals and vals['template_id'] != request.template_id.id:
                raise ValidationError(_("Template binding cannot be changed once a request is versioned."))
            if 'template_version_id' in vals and vals['template_version_id'] != request.template_version_id.id:
                raise ValidationError(_("Template version binding cannot be changed once a request is versioned."))
            if 'source_pdf_sha256' in vals and (vals['source_pdf_sha256'] or False) != (request.source_pdf_sha256 or False):
                raise ValidationError(_("Source PDF digest cannot be changed once a request is versioned."))

    @api.depends('signer_ids.state')
    def _compute_signer_counts(self):
        for request in self:
            signer_states = request.signer_ids.mapped('state')
            request.signed_count = signer_states.count('signed')
            request.pending_count = sum(state in {'pending', 'opened'} for state in signer_states)
            request.declined_count = signer_states.count('declined')

    def _check_can_send(self):
        for request in self:
            if not request.signer_ids:
                raise ValidationError(_("Cannot send a request without at least one signer."))
            if not request._get_actionable_signers():
                raise ValidationError(_("Cannot send a request without at least one pending or opened signer."))

    def write(self, vals):
        vals = self._sanitize_retention_fields_on_write(vals)
        self._guard_terminal_request_mutation(vals)
        self._check_binding_immutability(vals)
        bypass_transition_check = (
            self.env.su
            and self.env.context.get('open_sign_skip_transition_check')
        )
        if 'status' in vals and not bypass_transition_check:
            self._check_transition(vals['status'])
        return super().write(vals)

    def unlink(self):
        self.check_access('unlink')
        if self._can_hard_delete_request():
            return super().unlink()
        self.with_context(open_sign_soft_delete=True).write({
            'active': False,
            'deleted_at': fields.Datetime.now(),
        })
        return True

    def _check_transition(self, target_status):
        if target_status not in ALLOWED_STATUS_TRANSITIONS:
            raise ValidationError(_("Unknown target status: %(status)s", status=target_status))
        for request in self:
            if request.status == target_status:
                continue
            if target_status not in ALLOWED_STATUS_TRANSITIONS.get(request.status, set()):
                raise ValidationError(_(
                    "Invalid status transition from %(from_status)s to %(to_status)s.",
                    from_status=request.status,
                    to_status=target_status,
                ))

    def _transition_to(self, target_status, extra_vals=None):
        vals = {'status': target_status}
        if extra_vals:
            vals.update(extra_vals)
        self.write(vals)

    def _compute_status(self):
        # Placeholder for signer-driven state recomputation introduced in follow-up tasks.
        return {request.id: request.status for request in self}

    def _get_actionable_signers(self):
        self.ensure_one()
        candidates = self.signer_ids.filtered(lambda signer: signer.state in {'pending', 'opened'})
        if not candidates:
            return candidates
        if not self.ordered_signing:
            return candidates.sorted(lambda signer: (signer.sequence, signer.id))
        first_sequence = min(candidates.mapped('sequence'))
        return candidates.filtered(lambda signer: signer.sequence == first_sequence).sorted(lambda signer: (signer.sequence, signer.id))

    def action_version(self):
        now = fields.Datetime.now()
        for request in self:
            if request.template_id.state != 'published':
                raise ValidationError(_("Template must be published before request versioning."))
            version = request.template_id.action_publish_version()
            request._transition_to('versioned', {
                'template_version_id': version.id,
                'source_pdf_sha256': version.source_pdf_sha256,
                'last_event_at': now,
            })

    def action_send(self):
        now = fields.Datetime.now()
        for request in self:
            request._check_transition('sent')
            request._check_can_send()
            request._transition_to('sent', {
                'sent_at': request.sent_at or now,
                'last_event_at': now,
            })

    def action_cancel(self):
        now = fields.Datetime.now()
        for request in self:
            request._transition_to('cancelled', {'last_event_at': now})

    def action_complete(self):
        now = fields.Datetime.now()
        for request in self:
            if not request.final_attachment_id:
                raise ValidationError(_("Completed requests require a final attachment."))
            if not request.final_pdf_sha256:
                raise ValidationError(_("Completed requests require a final PDF SHA-256 digest."))
            request._transition_to('completed', {
                'completed_at': request.completed_at or now,
                'last_event_at': now,
            })

    def action_void(self, reason=None):
        del reason  # reason persistence is added with audit log implementation.
        now = fields.Datetime.now()
        for request in self:
            request._transition_to('voided', {'last_event_at': now})

    def generate_final_pdf(self):
        raise ValidationError(_("Final PDF generation is not implemented yet."))

    @api.constrains('template_version_id', 'template_id')
    def _check_template_version_belongs_to_template(self):
        for request in self.filtered('template_version_id'):
            if request.template_version_id.template_id != request.template_id:
                raise ValidationError(_("Template version must belong to the selected template."))

    @api.constrains('template_version_id', 'source_pdf_sha256')
    def _check_source_digest_matches_version(self):
        for request in self.filtered('template_version_id'):
            if request.source_pdf_sha256 and request.source_pdf_sha256 != request.template_version_id.source_pdf_sha256:
                raise ValidationError(_("Source digest must match the selected template version digest."))

    @api.constrains('source_pdf_sha256', 'final_pdf_sha256')
    def _check_digest_formats(self):
        for request in self:
            if request.source_pdf_sha256 and not SHA256_HEX_RE.fullmatch(request.source_pdf_sha256):
                raise ValidationError(_("Source PDF SHA-256 must be a 64-character lowercase hexadecimal string."))
            if request.final_pdf_sha256 and not SHA256_HEX_RE.fullmatch(request.final_pdf_sha256):
                raise ValidationError(_("Final PDF SHA-256 must be a 64-character lowercase hexadecimal string."))

    @api.constrains('status', 'template_version_id', 'source_pdf_sha256', 'completed_at', 'final_attachment_id', 'final_pdf_sha256')
    def _check_status_requirements(self):
        for request in self:
            if request.status in VERSION_REQUIRED_STATUSES:
                if not request.template_version_id or not request.source_pdf_sha256:
                    raise ValidationError(_(
                        "Status %(status)s requires template version and source digest.",
                        status=request.status,
                    ))
            if request.status == 'completed':
                if not request.completed_at:
                    raise ValidationError(_("Completed requests require completed_at timestamp."))
                if not request.final_attachment_id:
                    raise ValidationError(_("Completed requests require a final attachment."))
                if not request.final_pdf_sha256:
                    raise ValidationError(_("Completed requests require a final PDF SHA-256 digest."))

    @api.constrains('sent_at', 'expires_at')
    def _check_expiration_not_before_sent(self):
        for request in self.filtered(lambda rec: rec.sent_at and rec.expires_at):
            if request.expires_at < request.sent_at:
                raise ValidationError(_("Expiration datetime must be greater than or equal to sent datetime."))
