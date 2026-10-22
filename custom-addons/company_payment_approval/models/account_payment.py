from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    needs_payment_approval = fields.Boolean(
        string='Cần duyệt thanh toán',
        compute='_compute_payment_approval',
        store=True,
    )
    payment_approval_state = fields.Selection(
        selection=[
            ('not_required', 'Không cần duyệt'),
            ('to_approve', 'Chờ duyệt'),
            ('approved', 'Đã duyệt'),
            ('refused', 'Từ chối'),
        ],
        string='Trạng thái duyệt thanh toán',
        default='not_required',
        copy=False,
        tracking=True,
    )
    payment_approver_id = fields.Many2one(
        'res.users',
        string='Người duyệt thanh toán',
        copy=False,
        readonly=True,
    )
    payment_approval_date = fields.Datetime(
        string='Ngày duyệt thanh toán',
        copy=False,
        readonly=True,
    )
    payment_approval_note = fields.Text(
        string='Ghi chú duyệt thanh toán',
        copy=False,
    )

    @api.depends(
        'payment_type',
        'amount',
        'currency_id',
        'date',
        'company_id',
        'company_id.payment_approval_enabled',
        'company_id.payment_approval_limit',
    )
    def _compute_payment_approval(self):
        for payment in self:
            company = payment.company_id or self.env.company
            needs = False
            if company.payment_approval_enabled and payment.payment_type == 'outbound':
                amount = payment.amount or 0.0
                if payment.currency_id and payment.currency_id != company.currency_id:
                    amount = payment.currency_id._convert(
                        amount,
                        company.currency_id,
                        company,
                        payment.date or fields.Date.today(),
                    )
                needs = amount > (company.payment_approval_limit or 0.0)
            payment.needs_payment_approval = needs

    def write(self, vals):
        res = super().write(vals)
        business_fields = {
            'amount', 'payment_type', 'partner_id', 'journal_id',
            'currency_id', 'date', 'company_id',
        }
        if business_fields.intersection(vals):
            for payment in self:
                if not payment.needs_payment_approval:
                    if payment.payment_approval_state != 'not_required':
                        payment.write({
                            'payment_approval_state': 'not_required',
                            'payment_approver_id': False,
                            'payment_approval_date': False,
                        })
                elif payment.payment_approval_state in ('approved', 'refused'):
                    payment.write({
                        'payment_approval_state': 'to_approve',
                        'payment_approver_id': False,
                        'payment_approval_date': False,
                    })
        return res

    def action_post(self):
        for payment in self:
            if (
                payment.state in (False, 'draft')
                and payment.needs_payment_approval
                and payment.payment_approval_state != 'approved'
            ):
                raise UserError(_(
                    'Phiếu thanh toán %(payment)s cần được duyệt trước khi xác nhận.\n'
                    'Số tiền: %(amount).2f %(currency)s - Hạn mức tự động: %(limit).2f %(company_currency)s.'
                ) % {
                    'payment': payment.display_name,
                    'amount': payment.amount or 0.0,
                    'currency': payment.currency_id.name or '',
                    'limit': payment.company_id.payment_approval_limit or 0.0,
                    'company_currency': payment.company_id.currency_id.name or '',
                })
        return super().action_post()

    def action_request_payment_approval(self):
        for payment in self:
            if not payment.needs_payment_approval:
                payment.write({
                    'payment_approval_state': 'not_required',
                    'payment_approver_id': False,
                    'payment_approval_date': False,
                })
            else:
                payment.write({
                    'payment_approval_state': 'to_approve',
                    'payment_approver_id': False,
                    'payment_approval_date': False,
                })

    def action_approve_payment(self):
        if not self.env.user.has_group(
                'company_payment_approval.group_payment_approval_manager'):
            raise UserError(_('Chỉ quản lý kế toán mới được duyệt thanh toán.'))
        for payment in self:
            if not payment.needs_payment_approval:
                payment.write({'payment_approval_state': 'not_required'})
                continue
            payment.write({
                'payment_approval_state': 'approved',
                'payment_approver_id': self.env.user.id,
                'payment_approval_date': fields.Datetime.now(),
            })

    def action_refuse_payment(self):
        if not self.env.user.has_group(
                'company_payment_approval.group_payment_approval_manager'):
            raise UserError(_('Chỉ quản lý kế toán mới được từ chối duyệt thanh toán.'))
        for payment in self:
            payment.write({
                'payment_approval_state': 'refused',
                'payment_approver_id': self.env.user.id,
                'payment_approval_date': fields.Datetime.now(),
            })

    def action_reset_payment_approval(self):
        for payment in self:
            payment.write({
                'payment_approval_state': 'not_required',
                'payment_approver_id': False,
                'payment_approval_date': False,
            })
