from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    payment_approval_enabled = fields.Boolean(
        string='Bật duyệt thanh toán',
        default=True,
        help='Yêu cầu quản lý kế toán duyệt các phiếu chi vượt hạn mức trước khi xác nhận.',
    )
    payment_approval_limit = fields.Monetary(
        string='Hạn mức thanh toán tự động',
        currency_field='currency_id',
        default=5000.0,
        help='Phiếu chi có giá trị (quy đổi về tiền tệ công ty) lớn hơn mức này '
             'phải được duyệt trước khi Confirm.',
    )
