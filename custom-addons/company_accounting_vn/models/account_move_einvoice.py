from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    """Trường hóa đơn điện tử theo NĐ 254/2026/NĐ-CP, bổ sung cho company_einvoice.

    Tái dùng ``einvoice_number`` (số hóa đơn) và ``einvoice_serial`` (ký hiệu) đã có,
    ``einvoice_symbol`` chỉ là bí danh của ``einvoice_serial``.
    """
    _inherit = 'account.move'

    einvoice_symbol = fields.Char(
        string='E-Invoice Symbol (Decree 254)', related='einvoice_serial', readonly=False)
    einvoice_date = fields.Date(string='E-Invoice Date', copy=False)
    einvoice_tax_authority_code = fields.Char(string='Tax Authority Code', copy=False)

    def _prepare_einvoice_payload(self):
        payload = super()._prepare_einvoice_payload()
        payload['decree_254'] = {
            'symbol': self.einvoice_serial or payload.get('serial') or '',
            'number': self.einvoice_number or '',
            'date': fields.Date.to_string(self.einvoice_date or self.invoice_date or fields.Date.today()),
            'tax_authority_code': self.einvoice_tax_authority_code or '',
        }
        return payload

    def action_einvoice_dry_run(self):
        """Run the existing e-invoice flow against a provider that is in dry-run mode only."""
        self.ensure_one()
        provider = self.einvoice_provider_id or self.env['company.einvoice.provider'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ], limit=1)
        if not provider:
            raise UserError(_('No e-invoice provider is configured.'))
        if not provider.dry_run:
            raise UserError(_('The dry run only works with a provider in dry-run mode.'))
        return self.action_send_einvoice()
