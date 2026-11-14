"""Sổ quỹ / sổ tiền gửi phải gồm cả phát sinh qua account.payment (ghi vào TK trung gian)."""
from odoo.tests import tagged

from .ledger_test_base import LedgerCommon


@tagged('post_install', '-at_install')
class TestLedgerCashBank(LedgerCommon):

    def _payment(self, payment_type, amount, journal):
        payment = self.env['account.payment'].create({
            'payment_type': payment_type,
            'partner_type': 'customer' if payment_type == 'inbound' else 'supplier',
            'partner_id': self.partner.id, 'amount': amount, 'journal_id': journal.id, 'date': '2026-02-12'})
        payment.action_post()
        return payment

    def test_cash_book_includes_payment_through_outstanding_account(self):
        payment = self._payment('inbound', 700000, self.cash_journal)
        raw_debit = payment.move_id.line_ids.filtered(lambda line: line.debit > 0).account_id
        self.assertNotEqual(raw_debit.vn_display_code, '111')  # bút toán lưu ở TK trung gian
        rows = self.rows('cash')
        section = self.section(rows, self.cash_journal.name)
        receipt = [r for r in section if r['kind'] == 'line' and r['voucher'] == payment.move_id.name]
        self.assertEqual(len(receipt), 1)
        self.assertEqual(receipt[0]['debit'], 700000.0)
        self.assertEqual(next(r for r in section if r['kind'] == 'close')['bal_debit'], 700000.0)
        # Dòng 111 của bút toán thường vẫn hiện, ở nhóm sổ nhật ký chứa nó.
        misc = self.section(rows, self.misc_journal.name)
        self.assertEqual(next(r for r in misc if r['kind'] == 'close')['bal_debit'], 1300000.0)
        # Tổng thu trong kỳ: phiếu thu 111 (300.000) + thu qua payment (700.000).
        self.assertEqual(rows[-1]['debit'], 300000.0 + 700000.0)

    def test_cash_book_payment_outbound_and_period_filter(self):
        self._payment('outbound', 50000, self.cash_journal)
        section = self.section(self.rows('cash'), self.cash_journal.name)
        self.assertEqual(next(r for r in section if r['kind'] == 'close')['bal_credit'], 50000.0)
        # Trước ngày thanh toán, nhóm sổ quỹ không có gì.
        early = self.rows('cash', date_from='2026-01-01', date_to='2026-02-11')
        self.assertFalse([r for r in early if r['kind'] == 'group' and self.cash_journal.name in r['label']])

    def test_bank_book_has_bank_payment_and_excludes_cash(self):
        bank = self.env['account.journal'].search([
            ('company_id', '=', self.company.id), ('type', '=', 'bank')], limit=1)
        self.assertTrue(bank)
        self._payment('inbound', 400000, bank)
        self._payment('inbound', 1000, self.cash_journal)
        rows = self.rows('bank')
        self.assertEqual(rows[-1]['debit'], 400000.0)
        self.assertEqual(self.section(rows, bank.name)[-1]['bal_debit'], 400000.0)
