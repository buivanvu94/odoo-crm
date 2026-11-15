from odoo.tests import tagged

from .vn_accounting_test_base import VNAccountingCommon

# 71 tài khoản cấp 1 theo Phụ lục II TT 99/2025/TT-BTC.
LEVEL1_CODES = {
    '111', '112', '113', '121', '128', '131', '133', '136', '138', '141', '151', '152', '153', '154',
    '155', '156', '157', '158', '171', '211', '212', '213', '214', '215', '217', '221', '222', '228',
    '229', '241', '242', '243', '244', '331', '332', '333', '334', '335', '336', '337', '338', '341',
    '343', '344', '347', '352', '353', '356', '357', '411', '412', '413', '414', '418', '419', '421',
    '511', '515', '521', '621', '622', '623', '627', '632', '635', '641', '642', '711', '811', '821',
    '911',
}
REMOVED_CODES = ('161', '417', '441', '461', '466', '611', '631')


@tagged('post_install', '-at_install')
class TestChartOfAccounts(VNAccountingCommon):

    def setUp(self):
        super().setUp()
        self.codes = set(self.env['account.account'].search(
            [('company_ids', 'in', self.company.id)]).mapped('code'))

    def test_template_loaded(self):
        self.assertEqual(self.company.chart_template, 'vn_tt99')
        self.assertEqual(self.company.accounting_regime, 'tt99')

    def test_71_level1_accounts(self):
        self.assertEqual(len(LEVEL1_CODES), 71)
        self.assertEqual({code[:3] for code in self.codes}, LEVEL1_CODES)

    def test_removed_and_new_accounts(self):
        for removed in REMOVED_CODES:
            self.assertFalse([c for c in self.codes if c.startswith(removed)], removed)
        for present in ('215', '332', '8212'):
            self.assertTrue([c for c in self.codes if c.startswith(present)], present)

    def test_account_types_and_reconcile(self):
        for code, account_type in (('131', 'asset_receivable'), ('141', 'asset_receivable'),
                                   ('331', 'liability_payable')):
            account = self.account(code)
            self.assertEqual(account.account_type, account_type, code)
            self.assertTrue(account.reconcile, code)
        # Tax accounts are not partner receivable/payable accounts.
        for code in ('133', '1331', '333', '3331', '33311'):
            account = self.account(code)
            self.assertNotIn(account.account_type, ('asset_receivable', 'liability_payable'), code)
            self.assertFalse(account.reconcile, code)

    def test_vat_taxes(self):
        taxes = self.env['account.tax'].search([('company_id', '=', self.company.id)])
        for use in ('sale', 'purchase'):
            rates = set(taxes.filtered(
                lambda t: t.type_tax_use == use and t.amount_type == 'percent').mapped('amount'))
            self.assertTrue({0.0, 5.0, 8.0, 10.0} <= rates, use)
        self.assertIn('VAT EXEMPTION', taxes.tax_group_id.mapped('name'))
        self.assertEqual(self.company.account_sale_tax_id.amount, 10.0)

    def test_account_attributes(self):
        self.assertEqual(self.account('131').vn_account_class, '1')
        self.assertEqual(self.account('511').vn_account_class, '5')
        for code in ('131', '331', '141'):
            self.assertTrue(self.account(code).vn_partner_required, code)
        self.assertFalse(self.account('111').vn_partner_required)
        self.assertEqual(self.account('111').vn_display_code, '111')
        self.assertEqual(self.account('1331').vn_display_code, '1331')
