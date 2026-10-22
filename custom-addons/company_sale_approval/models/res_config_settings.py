from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_max_discount = fields.Float(
        related='company_id.sale_max_discount',
        readonly=False,
        string='Giới hạn chiết khấu (%)',
    )
    sale_check_below_cost = fields.Boolean(
        related='company_id.sale_check_below_cost',
        readonly=False,
        string='Chặn bán dưới giá vốn',
    )
