import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    einvoice_provider_id = fields.Many2one(
        'company.einvoice.provider', string='Nhà cung cấp HĐĐT')
    einvoice_state = fields.Selection(
        selection=[
            ('none', 'Chưa gửi'),
            ('pending', 'Chờ phát hành'),
            ('issued', 'Đã phát hành'),
            ('failed', 'Lỗi'),
        ],
        string='Trạng thái HĐĐT',
        default='none',
        copy=False,
        tracking=True,
    )
    einvoice_number = fields.Char(string='Số hóa đơn điện tử', copy=False)
    einvoice_serial = fields.Char(string='Ký hiệu HĐĐT', copy=False)
    einvoice_issued_at = fields.Datetime(string='Thời điểm phát hành', copy=False)
    einvoice_error = fields.Char(string='Lỗi HĐĐT', copy=False)
    einvoice_payload = fields.Text(string='Payload gửi đi', copy=False)
    einvoice_response = fields.Text(string='Phản hồi nhà cung cấp', copy=False)

    def _prepare_einvoice_payload(self):
        self.ensure_one()
        provider = self.einvoice_provider_id
        if not provider:
            provider = self.env['company.einvoice.provider'].search([
                ('company_id', '=', self.company_id.id),
                ('active', '=', True),
            ], limit=1)
        if not provider:
            raise UserError(_('Chưa cấu hình nhà cung cấp hóa đơn điện tử.'))
        partner = self.commercial_partner_id
        address = ', '.join(filter(None, [
            partner.street,
            partner.street2,
            partner.city,
            partner.state_id.name,
            partner.country_id.name,
        ]))
        lines = []
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            lines.append({
                'name': line.name or line.product_id.display_name,
                'quantity': line.quantity,
                'unit_price': line.price_unit,
                'discount': line.discount,
                'tax_rate': [tax.amount for tax in line.tax_ids],
                'subtotal': line.price_subtotal,
                'total': line.price_total,
            })
        return {
            'provider': provider.code,
            'template_code': provider.template_code,
            'serial': provider.serial,
            'seller': {
                'name': self.company_id.name,
                'tax_code': self.company_id.vat or '',
                'address': ', '.join(filter(None, [
                    self.company_id.street,
                    self.company_id.city,
                    self.company_id.country_id.name,
                ])),
            },
            'buyer': {
                'name': partner.name or '',
                'tax_code': partner.vat or '',
                'address': address,
                'email': partner.email or '',
                'phone': partner.phone or '',
            },
            'invoice': {
                'reference': self.name,
                'date': fields.Date.to_string(self.invoice_date or fields.Date.today()),
                'currency': self.currency_id.name,
                'payment_method': self.invoice_payment_term_id.name or 'TM/CK',
            },
            'lines': lines,
            'totals': {
                'subtotal': self.amount_untaxed,
                'tax': self.amount_tax,
                'total': self.amount_total,
            },
        }

    def action_prepare_einvoice(self):
        for move in self:
            payload = move._prepare_einvoice_payload()
            provider = move.einvoice_provider_id or self.env['company.einvoice.provider'].search([
                ('company_id', '=', move.company_id.id),
                ('active', '=', True),
            ], limit=1)
            move.write({
                'einvoice_provider_id': provider.id,
                'einvoice_payload': json.dumps(payload, ensure_ascii=False, indent=2),
                'einvoice_state': 'pending',
                'einvoice_error': False,
            })

    def action_send_einvoice(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            raise UserError(_('Chỉ gửi hóa đơn điện tử cho hóa đơn khách hàng.'))
        if self.state != 'posted':
            raise UserError(_('Hóa đơn phải được xác nhận (Posted) trước khi gửi.'))
        if self.einvoice_state == 'issued':
            raise UserError(_('Hóa đơn đã được phát hành điện tử.'))
        payload = self._prepare_einvoice_payload()
        provider = self.einvoice_provider_id or self.env['company.einvoice.provider'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ], limit=1)
        self.write({
            'einvoice_provider_id': provider.id,
            'einvoice_payload': json.dumps(payload, ensure_ascii=False, indent=2),
            'einvoice_state': 'pending',
            'einvoice_error': False,
        })
        try:
            ok, response_text = provider._send_invoice(payload)
        except Exception as exc:  # noqa: BLE001 - network/providers raise many exceptions
            _logger.exception('E-invoice sending failed for %s', self.name)
            self.write({
                'einvoice_state': 'failed',
                'einvoice_error': str(exc)[:250],
                'einvoice_response': str(exc)[:10000],
            })
            return self._einvoice_notification(False, str(exc))
        number = self._extract_einvoice_number(response_text)
        is_dry_run = provider.dry_run
        self.write({
            'einvoice_response': (response_text or '')[:10000],
            'einvoice_state': 'pending' if is_dry_run else ('issued' if ok else 'failed'),
            'einvoice_number': number if not is_dry_run else False,
            'einvoice_serial': provider.serial if not is_dry_run else False,
            'einvoice_issued_at': fields.Datetime.now() if ok and not is_dry_run else False,
            'einvoice_error': False if ok else (response_text or '')[:250],
        })
        message = _('Chạy thử: payload đã tạo, chưa gửi nhà cung cấp.') if is_dry_run else (
            _('Đã gửi hóa đơn điện tử.') if ok else _('Gửi hóa đơn thất bại.'))
        return self._einvoice_notification(ok, message)

    @api.model
    def _extract_einvoice_number(self, response_text):
        try:
            data = json.loads(response_text or '{}')
        except ValueError:
            return False
        if not isinstance(data, dict):
            return False
        for key in ('invoice_number', 'invoiceNo', 'number', 'invoice_no'):
            if data.get(key):
                return str(data[key])
        nested = data.get('data')
        if isinstance(nested, dict):
            for key in ('invoice_number', 'invoiceNo', 'number', 'invoice_no'):
                if nested.get(key):
                    return str(nested[key])
        return False

    def _einvoice_notification(self, ok, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Hóa đơn điện tử'),
                'message': message,
                'type': 'success' if ok else 'danger',
                'sticky': False,
            },
        }
