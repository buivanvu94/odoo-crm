from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_approval_enabled = fields.Boolean(
        related='company_id.payment_approval_enabled',
        readonly=False,
        string='Bật duyệt thanh toán',
    )
    payment_approval_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
        string='Payment Approval Currency',
    )
    payment_approval_limit = fields.Monetary(
        related='company_id.payment_approval_limit',
        readonly=False,
        currency_field='payment_approval_currency_id',
        string='Hạn mức thanh toán tự động',
    )
