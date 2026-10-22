from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

APPROVER_GROUP = 'company_approval.group_approval_manager'


class CompanyApprovalRequest(models.Model):
    _name = 'company.approval.request'
    _description = 'Internal Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc, id desc'

    name = fields.Char(
        string='Reference', default='/', required=True, copy=False, readonly=True, index=True,
    )
    request_type = fields.Selection(
        selection=[
            ('purchase', 'Purchase'),
            ('payment', 'Payment'),
            ('leave', 'Leave'),
            ('other', 'Other'),
        ],
        string='Type', required=True, default='purchase', tracking=True,
    )
    requested_by = fields.Many2one(
        'res.users', string='Requested By',
        default=lambda self: self.env.user, required=True, index=True, tracking=True,
    )
    approver_id = fields.Many2one(
        'res.users', string='Approver', readonly=True, tracking=True,
    )
    date_request = fields.Date(
        string='Request Date', default=fields.Date.context_today, required=True, tracking=True,
    )
    date_approval = fields.Datetime(string='Approval Date', readonly=True)
    amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id, required=True,
    )
    reason = fields.Text(string='Reason', required=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('refused', 'Refused'),
        ],
        string='Status', default='draft', required=True, copy=False, index=True, tracking=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('company.approval.request') or '/'
        return super().create(vals_list)

    def action_submit(self):
        for request in self:
            if request.state != 'draft':
                raise UserError(self.env._("Only draft requests can be submitted."))
            request.state = 'submitted'

    def action_approve(self):
        if not self.env.user.has_group(APPROVER_GROUP):
            raise AccessError(self.env._("Only approvers can approve a request."))
        for request in self:
            if request.state != 'submitted':
                raise UserError(self.env._("Only submitted requests can be approved."))
            request.write({
                'state': 'approved',
                'approver_id': self.env.user.id,
                'date_approval': fields.Datetime.now(),
            })

    def action_refuse(self):
        if not self.env.user.has_group(APPROVER_GROUP):
            raise AccessError(self.env._("Only approvers can refuse a request."))
        for request in self:
            if request.state != 'submitted':
                raise UserError(self.env._("Only submitted requests can be refused."))
            request.write({
                'state': 'refused',
                'approver_id': self.env.user.id,
                'date_approval': fields.Datetime.now(),
            })

    def action_reset_draft(self):
        for request in self:
            if request.state == 'draft':
                raise UserError(self.env._("This request is already in draft."))
            request.write({
                'state': 'draft',
                'approver_id': False,
                'date_approval': False,
            })
