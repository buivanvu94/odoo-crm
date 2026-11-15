"""Sổ và bút toán của công ty B phải đúng khi người dùng đang đứng ở công ty A (mã TK phụ thuộc công ty)."""
import io
import zipfile

from odoo.exceptions import UserError
from odoo.tests import tagged

from .multi_company_test_base import MultiCompanyCommon


@tagged('post_install', '-at_install')
class TestCompanyContext(MultiCompanyCommon):

    def _wizard(self, report_type, **extra):
        return self.env_a['accounting.report.wizard'].with_user(self.accountant).create({
            'company_id': self.company_b.id, 'report_type': report_type,
            'date_from': '2026-02-01', 'date_to': '2026-02-28', **extra})

    def test_books_of_other_company_are_not_empty(self):
        self.entry_of(self.company_b, [('111', 500000, 0), ('411', 0, 500000)])
        self.assertEqual(self._wizard('cash')._get_report_data()['rows'][-1]['debit'], 500000.0)
        trial = self._wizard('trial')._get_report_data()['rows']
        self.assertEqual({r['account'] for r in trial if r['kind'] == 'group'}, {'111', '411'})
        # Chọn TK theo mã cũng phải tìm đúng TK của công ty B.
        ledger = self._wizard('ledger', account_ids=[self.account_of(self.company_b, '111').id])
        self.assertEqual(ledger._get_report_data()['rows'][-1]['debit'], 500000.0)

    def test_pdf_and_excel_use_wizard_company(self):
        self.entry_of(self.company_b, [('111', 500000, 0), ('411', 0, 500000)])
        wizard = self._wizard('cash')
        values = self.env_a['report.company_accounting_vn.report_vn_ledger'].with_user(
            self.accountant)._get_report_values(wizard.ids)
        self.assertEqual(values['reports'][wizard.id]['rows'][-1]['debit'], 500000.0)
        wizard.action_export_xlsx()
        with zipfile.ZipFile(io.BytesIO(wizard.xlsx_file)) as book:
            self.assertIn('500000', book.read('xl/worksheets/sheet1.xml').decode())

    def test_screen_view_uses_wizard_company(self):
        self.entry_of(self.company_b, [('111', 500000, 0), ('411', 0, 500000)])
        wizard = self._wizard('cash')
        wizard.action_view_screen()
        self.assertEqual(wizard.line_ids.filtered(lambda line: line.kind == 'grand').debit, 500000.0)

    def test_post_checks_partner_with_move_company(self):
        with self.assertRaises(UserError):
            self.entry_of(self.company_b, [('131', 100000, 0), ('511', 0, 100000)])
        move = self.entry_of(self.company_b, [('131', 100000, 0, self.partner), ('511', 0, 100000)])
        self.assertEqual(move.state, 'posted')

    def test_counterparts_use_move_company_codes(self):
        move = self.entry_of(self.company_b, [('131', 100000, 0, self.partner), ('511', 0, 100000)])
        by_name = {line.name: line for line in move.line_ids}
        self.assertEqual(by_name['131'].counterpart_name, '511')
        self.assertEqual(by_name['511'].counterpart_name, '131')

    def test_display_code_depends_on_company_context(self):
        account = self.account_of(self.company_b, '131')
        self.assertEqual(account.with_company(self.company_b).vn_display_code, '131')
        self.assertTrue(account.with_company(self.company_b).vn_partner_required)
        # Cùng bản ghi, đọc từ công ty A: không được dùng lại giá trị đã cache của công ty B.
        self.assertNotEqual(account.with_company(self.company_a).vn_display_code, '131')

    def test_payment_voucher_codes_use_payment_company(self):
        journal = self.env_a['account.journal'].search([
            ('company_id', '=', self.company_b.id), ('type', '=', 'cash')], limit=1)
        payment = self.env_a['account.payment'].with_company(self.company_b).create({
            'payment_type': 'inbound', 'partner_type': 'customer', 'partner_id': self.partner.id,
            'amount': 100000.0, 'journal_id': journal.id, 'date': '2026-02-10'})
        payment.with_company(self.company_a).action_post()
        for record in (payment, payment.with_company(self.company_a)):
            data = record._get_voucher_data()
            self.assertEqual(data['debit_codes'], '111')
            self.assertTrue(data['credit_codes'].startswith('131'))
        html, _kind = self.env_a['ir.actions.report']._render_qweb_html(
            'company_accounting_vn.action_report_payment_receipt', payment.ids)
        self.assertIn('131', html.decode())  # TK phải thu của công ty B hiện trên mẫu in
