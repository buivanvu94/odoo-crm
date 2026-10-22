from odoo.tests.common import TransactionCase


class TestEinvoice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env['company.einvoice.provider'].create({
            'name': 'VNPT Test',
            'code': 'vnpt',
            'dry_run': True,
        })

    def test_dry_run_send(self):
        ok, response = self.provider._send_invoice({'invoice': {'reference': 'INV/1'}})
        self.assertTrue(ok)
        self.assertIn('dry_run', response)

    def test_extract_invoice_number(self):
        move = self.env['account.move']
        self.assertEqual(
            move._extract_einvoice_number('{"data": {"invoiceNo": "HD001"}}'),
            'HD001',
        )
        self.assertEqual(move._extract_einvoice_number('{"invoice_number": "HD002"}'), 'HD002')
        self.assertFalse(move._extract_einvoice_number('not json'))
