from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True)
    internal_transfer_approval = fields.Boolean(
        related='company_id.internal_transfer_approval',
        readonly=False,
    )
    internal_transfer_limit = fields.Monetary(
        related='company_id.internal_transfer_limit',
        readonly=False,
        currency_field='company_currency_id',
    )
