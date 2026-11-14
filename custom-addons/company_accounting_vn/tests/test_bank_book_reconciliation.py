"""Sổ tiền gửi khi payment đối soát một phần / sau kỳ báo cáo / TK trung gian là TK con của 112, và các
đẳng thức giữa sổ quỹ, sổ tiền gửi, B01 và B03 khi sao kê chưa đối soát (TK treo không phải tiền)."""
from datetime import date

from odoo import Command
from odoo.tests import tagged

from .ledger_test_base import LedgerCommon


@tagged('post_install', '-at_install')
class TestBankBookReconciliation(LedgerCommon):

    def setUp(self):
        super().setUp()
        self.bank = self.env['account.journal'].search([
            ('company_id', '=', self.company.id), ('type', '=', 'bank')], limit=1)
        self.manager = self.env['res.users'].create({
            'name': 'vn_bank_manager', 'login': 'vn_bank_manager', 'company_id': self.company.id,
            'company_ids': [Command.set(self.company.ids)],
            'group_ids': [Command.set([self.env.ref('base.group_user').id,
                                       self.env.ref('account.group_account_manager').id])]})

    def _payment(self, day, amount=400000):
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound', 'partner_type': 'customer', 'partner_id': self.partner.id,
            'amount': amount, 'journal_id': self.bank.id, 'date': day})
        payment.action_post()
        return payment

    def _match(self, payment, day, amount):
        """Dòng sao kê đã khớp: Nợ TK ngân hàng / Có TK trung gian, đối soát (có thể một phần) với payment."""
        outstanding = payment.outstanding_account_id
        statement = self.env['account.move'].create({
            'move_type': 'entry', 'journal_id': self.bank.id, 'date': day, 'line_ids': [
                Command.create({'name': 'bank', 'account_id': self.bank.default_account_id.id, 'debit': amount}),
                Command.create({'name': 'clearing', 'account_id': outstanding.id, 'credit': amount})]})
        statement.action_post()
        pay_line = payment.move_id.line_ids.filtered(lambda line: line.account_id == outstanding)
        (pay_line + statement.line_ids.filtered(lambda line: line.account_id == outstanding)).reconcile()
        return pay_line

    def _bank_book(self, date_from, date_to):
        return self._book('bank', date_from, date_to)

    def _book(self, kind, date_from, date_to):
        """(tổng Nợ, tổng Có, số dư cuối) của sổ quỹ / sổ tiền gửi."""
        rows = self.rows(kind, date_from=date_from, date_to=date_to)
        closing = [r for r in rows if r['kind'] == 'close']
        balance = sum(r['bal_debit'] - r['bal_credit'] for r in closing)
        return rows[-1]['debit'], rows[-1]['credit'], balance

    def _b01(self, date_from, date_to):
        sections = self.env['vn.financial.report'].with_user(self.manager).build_all(
            ['b01', 'b03d'], self.company, date.fromisoformat(date_from), date.fromisoformat(date_to))
        return {(s['form_code'], row['code']): row['value'] for s in sections for row in s['rows'] if row['code']}

    def test_partially_matched_payment_is_counted_once(self):
        payment = self._payment('2026-02-12', 400000)
        pay_line = self._match(payment, '2026-02-13', 300000)
        self.assertFalse(pay_line.reconciled)
        self.assertEqual(pay_line.amount_residual, 100000.0)
        self.assertEqual(self._bank_book('2026-02-01', '2026-02-28'), (400000.0, 0.0, 400000.0))

    def test_closed_period_does_not_change_when_matched_later(self):
        payment = self._payment('2026-01-20', 400000)
        january = ('2026-01-01', '2026-01-31')
        before = self._bank_book(*january)
        self.assertEqual(before, (400000.0, 0.0, 400000.0))
        self._match(payment, '2026-03-05', 400000)
        self.assertEqual(self._bank_book(*january), before)
        self.assertEqual(self._bank_book('2026-02-01', '2026-02-28'), (0.0, 0.0, 400000.0))
        # Sau khi khớp, sao kê không tính lần nữa: tháng 3 không phát sinh, số dư cuối vẫn 400.000.
        self.assertEqual(self._bank_book('2026-03-01', '2026-03-31'), (0.0, 0.0, 400000.0))
        # Cùng kỳ, B01 mã 110 (tiền gồm cả TK trung gian 1131) khớp sổ tiền gửi + sổ quỹ.
        cash_balance = 1000000.0 + 300000.0
        self.assertEqual(self._b01(*january)['B01-DN', '110'], 1000000.0 + 400000.0)
        self.assertEqual(self._b01('2026-01-01', '2026-03-31')['B01-DN', '110'], cash_balance + 400000.0)

    def test_outstanding_account_under_112_is_not_a_main_account(self):
        account = self.env['account.account'].create({
            'code': '1122', 'name': 'Tiền gửi chờ đối soát', 'account_type': 'asset_current', 'reconcile': True})
        self.bank.inbound_payment_method_line_ids[:1].payment_account_id = account
        payment = self._payment('2026-02-12', 400000)
        self.assertEqual(payment.outstanding_account_id, account)
        self._match(payment, '2026-02-13', 400000)
        self.assertEqual(self._bank_book('2026-02-01', '2026-02-28'), (400000.0, 0.0, 400000.0))

    def test_unmatched_statement_keeps_books_and_statements_consistent(self):
        suspense = self.bank.suspense_account_id
        self.env['account.bank.statement.line'].create({
            'journal_id': self.bank.id, 'date': '2026-02-13', 'amount': 400000, 'payment_ref': 'sao kê'})
        period = ('2026-01-01', '2026-02-28')
        _cash_debit, _cash_credit, cash_balance = self._book('cash', *period)
        bank_debit, bank_credit, bank_balance = self._bank_book(*period)
        self.assertEqual((bank_debit, bank_credit), (400000.0, 0.0))
        values = self._b01(*period)
        # S07 + S08 = B01 mã 111 (TK treo 1121 không triệt tiêu 1120).
        self.assertEqual(values['B01-DN', '111'], cash_balance + bank_balance)
        self.assertEqual(values['B01-DN', '110'], values['B03-DN', '70'])
        self.assertEqual(values['B01-DN', '270'], values['B01-DN', '440'])
        # Số dư Có của TK treo là phải trả khác (mã 319), không bù vào tiền.
        self.assertEqual(values['B01-DN', '319'], 400000.0)
        self.assertTrue(suspense.vn_display_code.startswith('112'))

    def test_debit_balance_of_suspense_goes_to_other_receivables(self):
        self.env['account.bank.statement.line'].create({
            'journal_id': self.bank.id, 'date': '2026-02-13', 'amount': -150000, 'payment_ref': 'phí ngân hàng'})
        values = self._b01('2026-02-01', '2026-02-28')
        self.assertEqual(values['B01-DN', '136'], 150000.0)
        self.assertEqual(values['B01-DN', '270'], values['B01-DN', '440'])
        self.assertEqual(values['B01-DN', '110'], values['B03-DN', '70'])
