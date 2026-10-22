from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    internal_transfer_approval = fields.Boolean(
        string='Duyệt chuyển kho nội bộ',
        default=True,
    )
    internal_transfer_limit = fields.Monetary(
        string='Hạn mức chuyển kho tự động',
        currency_field='currency_id',
        default=5000.0,
        help='Phiếu chuyển kho nội bộ có giá trị vượt hạn mức này phải được quản lý kho duyệt.',
    )
