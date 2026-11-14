import json

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .vn_accounting_test_base import VNAccountingCommon


@tagged('post_install', '-at_install')
class TestEinvoiceDryRun(VNAccountingCommon):

    def _invoice(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.today(),
            'einvoice_tax_authority_code': 'CQT-001',
            'invoice_line_ids': [Command.create({'name': 'Dịch vụ', 'quantity': 1, 'price_unit': 500000})],
        })
        invoice.action_post()
        return invoice

    def _provider(self, dry_run):
        return self.env['company.einvoice.provider'].create({
            'name': 'VNPT Test', 'code': 'vnpt', 'dry_run': dry_run, 'serial': '1C26TBB',
            'company_id': self.company.id,
        })

    def test_dry_run_payload_has_decree_254_fields(self):
        self._provider(dry_run=True)
        invoice = self._invoice()
        invoice.action_einvoice_dry_run()
        payload = json.loads(invoice.einvoice_payload)
        self.assertEqual(payload['decree_254']['tax_authority_code'], 'CQT-001')
        self.assertEqual(payload['decree_254']['symbol'], '1C26TBB')
        self.assertIn('dry_run', invoice.einvoice_response)
        self.assertEqual(invoice.einvoice_state, 'pending')
        self.assertFalse(invoice.einvoice_number)

    def test_symbol_aliases_serial(self):
        invoice = self._invoice()
        invoice.einvoice_symbol = '1C26TAA'
        self.assertEqual(invoice.einvoice_serial, '1C26TAA')

    def test_real_provider_is_refused(self):
        self._provider(dry_run=False)
        invoice = self._invoice()
        with self.assertRaises(UserError):
            invoice.action_einvoice_dry_run()
        self.assertEqual(invoice.einvoice_state, 'none')

    def test_no_provider(self):
        with self.assertRaises(UserError):
            self._invoice().action_einvoice_dry_run()
