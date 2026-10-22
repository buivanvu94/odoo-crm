from odoo import fields, models


class CompanyShipmentLog(models.Model):
    _name = 'company.shipment.log'
    _description = 'Lịch sử tạo vận đơn'
    _order = 'create_date desc, id desc'

    picking_id = fields.Many2one('stock.picking', string='Phiếu kho', required=True, ondelete='cascade')
    carrier_id = fields.Many2one('delivery.carrier', string='Đơn vị vận chuyển')
    state = fields.Selection(
        selection=[
            ('draft', 'Nháp'),
            ('sent', 'Đã gửi API'),
            ('manual', 'Thủ công'),
            ('error', 'Lỗi'),
        ],
        string='Trạng thái',
        default='draft',
    )
    tracking_ref = fields.Char(string='Mã vận đơn')
    message = fields.Char(string='Thông báo')
    request_payload = fields.Text(string='Dữ liệu gửi')
    response_payload = fields.Text(string='Dữ liệu trả về')
    company_id = fields.Many2one(
        'res.company', related='picking_id.company_id', store=True, string='Công ty')
