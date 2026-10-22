from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    sale_max_discount = fields.Float(
        string='Giới hạn chiết khấu (%)',
        default=10.0,
        help='Chiết khấu tối đa trên một dòng hàng mà nhân viên được tự quyết định. '
             'Vượt mức này phải được quản lý duyệt giá.',
    )
    sale_check_below_cost = fields.Boolean(
        string='Chặn bán dưới giá vốn',
        default=True,
        help='Yêu cầu duyệt khi đơn giá sau chiết khấu thấp hơn giá vốn sản phẩm.',
    )
