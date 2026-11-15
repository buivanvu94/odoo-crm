"""Sổ quỹ / tiền gửi: TK treo của sao kê, payment đã đối soát, payment khác sổ nhật ký; giới hạn dòng màn hình."""
from odoo import Command
from odoo.tests import tagged

from .ledger_test_base import LedgerCommon


@tagged('post_install', '-at_install')
class TestLedgerReviewFixes(LedgerCommon):

    def setUp(self):
        super().setUp()
        self.bank = self.env['account.journal'].search([
            ('company_id', '=', self.company.id), ('type', '=', 'bank')], limit=1)

    def _payment(self, journal, amount=400000, payment_type='inbound'):
        payment = self.env['account.payment'].create({
            'payment_type': payment_type, 'partner_type': 'customer', 'partner_id': self.partner.id,
            'amount': amount, 'journal_id': journal.id, 'date': '2026-02-12'})
        payment.action_post()
        return payment

    def _statement_line(self, journal, amount):
        return self.env['account.bank.statement.line'].create({
            'journal_id': journal.id, 'date': '2026-02-13', 'amount': amount, 'payment_ref': 'sao kê'})

    def _codes(self, rows):
        return {r['account'] for r in rows if r['kind'] == 'line'}

    def test_statement_line_counts_once_without_suspense_side(self):
        self.assertTrue(self.bank.suspense_account_id.vn_display_code.startswith('112'))  # TK treo nằm trong 112
        self._statement_line(self.bank, 400000)
        rows = self.rows('bank')
        self.assertEqual((rows[-1]['debit'], rows[-1]['credit']), (400000.0, 0.0))
        self.assertNotIn(self.bank.suspense_account_id.vn_display_code, self._codes(rows))

    def test_cash_statement_does_not_leak_into_bank_book(self):
        self._statement_line(self.cash_journal, 1000)
        bank = self.rows('bank')
        self.assertEqual((bank[-1]['debit'], bank[-1]['credit']), (0.0, 0.0))
        cash = self.rows('cash')
        self.assertEqual(cash[-1]['debit'], 300000.0 + 1000.0)  # phiếu thu 111 của tháng 2 + dòng sao kê quỹ
        self.assertEqual(cash[-1]['credit'], 0.0)

    def test_reconciled_payment_is_counted_through_statement_only(self):
        payment = self._payment(self.bank)
        outstanding = payment.outstanding_account_id
        pay_line = payment.move_id.line_ids.filtered(lambda line: line.account_id == outstanding)
        # Dòng sao kê sau khi khớp với payment: Nợ TK ngân hàng / Có TK trung gian.
        statement = self.env['account.move'].create({
            'move_type': 'entry', 'journal_id': self.bank.id, 'date': '2026-02-13',
            'line_ids': [
                Command.create({'name': 'bank', 'account_id': self.bank.default_account_id.id, 'debit': 400000}),
                Command.create({'name': 'clearing', 'account_id': outstanding.id, 'credit': 400000})]})
        statement.action_post()
        (pay_line + statement.line_ids.filtered(lambda line: line.account_id == outstanding)).reconcile()
        self.assertTrue(pay_line.reconciled)
        rows = self.rows('bank')
        self.assertEqual((rows[-1]['debit'], rows[-1]['credit']), (400000.0, 0.0))

    def test_payment_of_other_journal_is_not_in_cash_book(self):
        self._payment(self.bank, 400000)  # cả hai loại payment cùng ghi vào TK trung gian 1131
        cash = self.rows('cash')
        self.assertEqual(cash[-1]['debit'], 300000.0)
        self.assertEqual(self.rows('bank')[-1]['debit'], 400000.0)

    def test_screen_rows_are_capped_with_notice_and_grand_total(self):
        self.env['ir.config_parameter'].sudo().set_int('company_accounting_vn.screen_row_limit', 5)
        wizard = self.wizard('journal')
        total_rows = len(wizard._get_report_data()['rows'])
        self.assertGreater(total_rows, 5)
        wizard.action_view_screen()
        lines = wizard.line_ids.sorted('sequence')
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0].kind, 'group')  # dòng thông báo bị cắt bớt
        self.assertEqual(lines[-1].kind, 'grand')
        self.assertEqual(lines[-1].debit, 500000.0 + 300000.0 + 200000.0)
        self.env['ir.config_parameter'].sudo().set_int('company_accounting_vn.screen_row_limit', 0)
        wizard.action_view_screen()
        self.assertEqual(len(wizard.line_ids), total_rows)

    def test_screen_row_limit_has_a_sensible_floor(self):
        self.env['ir.config_parameter'].sudo().set_int('company_accounting_vn.screen_row_limit', 1)
        wizard = self.wizard('journal')
        wizard.action_view_screen()
        lines = wizard.line_ids.sorted('sequence')
        self.assertEqual([line.kind for line in lines][0::2], ['group', 'grand'])
        self.assertEqual(len(lines), 3)  # thông báo, một dòng dữ liệu, tổng cộng
