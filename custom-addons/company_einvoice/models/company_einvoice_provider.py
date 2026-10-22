import json
import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CompanyEinvoiceProvider(models.Model):
    _name = 'company.einvoice.provider'
    _description = 'Nhà cung cấp hóa đơn điện tử'
    _order = 'sequence, name'

    name = fields.Char(string='Tên nhà cung cấp', required=True)
    code = fields.Selection(
        selection=[
            ('vnpt', 'VNPT Invoice'),
            ('viettel', 'Viettel SInvoice'),
            ('other', 'Khác'),
        ],
        string='Nhà cung cấp', required=True, default='vnpt',
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty', required=True,
        default=lambda self: self.env.company)
    endpoint = fields.Char(
        string='API Endpoint',
        help='URL API phát hành hóa đơn do nhà cung cấp cấp.',
    )
    username = fields.Char(string='Tài khoản')
    password = fields.Char(string='Mật khẩu')
    token = fields.Char(string='Access Token')
    template_code = fields.Char(string='Mẫu số hóa đơn')
    serial = fields.Char(string='Ký hiệu hóa đơn')
    dry_run = fields.Boolean(
        string='Chế độ chạy thử',
        default=True,
        help='Chỉ tạo payload, không gửi API. Dùng khi chưa có tài khoản thật.',
    )
    note = fields.Text(string='Ghi chú')

    def _send_invoice(self, payload):
        self.ensure_one()
        if self.dry_run:
            return True, json.dumps({
                'status': 'dry_run',
                'message': 'Chế độ chạy thử: chưa gửi tới nhà cung cấp.',
            }, ensure_ascii=False)
        if not self.endpoint:
            raise UserError(_('Chưa cấu hình API Endpoint cho nhà cung cấp %s.') % self.name)
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer %s' % self.token
        auth = None
        if self.username and self.password:
            auth = (self.username, self.password)
        response = requests.post(
            self.endpoint,
            json=payload,
            headers=headers,
            auth=auth,
            timeout=60,
        )
        _logger.info('E-invoice provider %s responded HTTP %s', self.name, response.status_code)
        return response.ok, response.text or ''
