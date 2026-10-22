from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    vn_carrier_type = fields.Selection(
        selection=[
            ('manual', 'Thủ công'),
            ('ghn', 'Giao Hàng Nhanh (GHN)'),
            ('viettelpost', 'Viettel Post'),
            ('other', 'Đơn vị khác'),
        ],
        string='Đơn vị vận chuyển VN',
        default='manual',
        help='Chọn đơn vị để dùng đúng mẫu dữ liệu khi tạo vận đơn.',
    )
    api_endpoint = fields.Char(
        string='API Endpoint',
        help='URL API tạo vận đơn, ví dụ https://online-gateway.ghn.vn/shiip/public-api/v2/shipping-order/create',
    )
    api_token = fields.Char(string='API Token')
    api_shop_id = fields.Char(string='Shop / Customer ID')
