"""Kiểm thử các sổ kế toán (S01, S02b, S31, bảng cân đối số phát sinh) với bút toán thật."""
import io
import zipfile

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .ledger_test_base import FEB, LedgerCommon



@tagged('post_install', '-at_install')
class TestLedgerBooks(LedgerCommon):

    def test_general_journal_balanced_and_posted_only(self):
        rows = self.rows('journal')
        lines = [r for r in rows if r['kind'] == 'line']
        self.assertEqual(len(lines), 6)  # bút toán nháp không xuất hiện
        grand = rows[-1]
        self.assertEqual(grand['debit'], grand['credit'])
        self.assertEqual(grand['debit'], 1000000.0)
        self.assertNotIn(self.draft.name, [r['voucher'] for r in lines])
        self.assertEqual(lines[0]['account'], '131')
        self.assertEqual(lines[0]['counterpart'], '511')

    def test_general_journal_partner_and_account_filters(self):
        rows = self.rows('journal', partner_ids=[Command.set(self.partner.ids)])
        self.assertEqual({r['account'] for r in rows if r['kind'] == 'line'}, {'131'})
        rows = self.rows('journal', account_ids=[Command.set(self.account('156').ids)])
        self.assertEqual([r['account'] for r in rows if r['kind'] == 'line'], ['156'])

    def test_ledger_opening_movement_closing(self):
        rows = self.rows('ledger', account_ids=[Command.set(self.account('111').ids)])
        section = self.section(rows, '111')
        opening = next(r for r in section if r['kind'] == 'open')
        total = next(r for r in section if r['kind'] == 'total')
        closing = next(r for r in section if r['kind'] == 'close')
        self.assertEqual(opening['bal_debit'], 1000000.0)
        self.assertEqual((total['debit'], total['credit']), (300000.0, 0.0))
        self.assertEqual(closing['bal_debit'], opening['bal_debit'] + total['debit'] - total['credit'])
        line = next(r for r in section if r['kind'] == 'line')
        self.assertEqual((line['counterpart'], line['bal_debit']), ('131', 1300000.0))

    def test_ledger_all_accounts_balanced_and_period_filter(self):
        rows = self.rows('ledger')
        grand = rows[-1]
        self.assertEqual(grand['debit'], grand['credit'])
        # Tháng 1 chỉ có một bút toán: số dư đầu kỳ bằng 0, cuối kỳ 1.000.000 ở TK 111 (Nợ) và 411 (Có).
        jan = self.rows('ledger', date_from='2026-01-01', date_to='2026-01-31')
        cash = self.section(jan, '111')
        self.assertEqual(next(r for r in cash if r['kind'] == 'open')['bal_debit'], 0.0)
        self.assertEqual(next(r for r in cash if r['kind'] == 'close')['bal_debit'], 1000000.0)
        equity = self.section(jan, '411')
        self.assertEqual(next(r for r in equity if r['kind'] == 'close')['bal_credit'], 1000000.0)

    def test_receivable_partner_book(self):
        rows = self.rows('partner_131')
        self.assertEqual([r['label'] for r in rows if r['kind'] == 'group'], [self.partner.display_name])
        section = self.section(rows, self.partner.name)
        self.assertEqual(next(r for r in section if r['kind'] == 'close')['bal_debit'], 200000.0)
        # Lọc kỳ: trước tháng 2 chưa có công nợ.
        self.assertEqual(len(self.rows('partner_131', date_from='2026-01-01', date_to='2026-01-31')), 1)

    def test_payable_partner_book_partner_filter(self):
        rows = self.rows('partner_331')
        close = next(r for r in rows if r['kind'] == 'close')
        self.assertEqual(close['bal_credit'], 200000.0)
        other = self.rows('partner_331', partner_ids=[Command.set(self.partner.ids)])
        self.assertEqual(len(other), 1)  # chỉ còn dòng tổng cộng rỗng

    def test_trial_balance(self):
        rows = self.rows('trial')
        grand = rows[-1]
        for opening, closing in (('open_debit', 'open_credit'), ('close_debit', 'close_credit'),
                                 ('debit', 'credit')):
            self.assertEqual(grand[opening], grand[closing])
        groups = {r['account']: r for r in rows if r['kind'] == 'group'}
        cash = groups['111']
        self.assertEqual((cash['open_debit'], cash['debit'], cash['credit'], cash['close_debit']),
                         (1000000.0, 300000.0, 0.0, 1300000.0))
        self.assertEqual(groups['131']['close_debit'], 200000.0)
        self.assertEqual(groups['411']['close_credit'], 1000000.0)
        for row in groups.values():  # đầu kỳ + phát sinh = cuối kỳ cho từng TK
            net_open = row['open_debit'] - row['open_credit']
            net_close = row['close_debit'] - row['close_credit']
            self.assertAlmostEqual(net_open + row['debit'] - row['credit'], net_close)

    def test_trial_balance_shows_sub_accounts(self):
        sub = self.account('1121')  # TK con của 112 có sẵn trong chart
        self.entry(FEB, [(sub.code, 50000, 0), ('411', 0, 50000)])
        rows = self.rows('trial')
        codes = [(r['kind'], r['account']) for r in rows]
        self.assertIn(('group', '112'), codes)
        self.assertIn(('line', '1121'), codes)
        self.assertEqual(next(r for r in rows if r['account'] == '112')['close_debit'], 50000.0)

    def test_screen_pdf_and_excel_outputs(self):
        wizard = self.wizard('ledger')
        action = wizard.action_view_screen()
        self.assertEqual(self.env['accounting.report.line'].search_count(action['domain']),
                         len(wizard._get_report_data()['rows']))
        html, _kind = self.env['ir.actions.report'].with_user(self.accountant)._render_qweb_html(
            'company_accounting_vn.report_vn_ledger', wizard.ids)
        html = html.decode() if isinstance(html, bytes) else html
        self.assertIn('SỔ CÁI', html)
        self.assertIn('Số dư đầu kỳ', html)
        url = wizard.action_export_xlsx()['url']
        self.assertIn('xlsx_file', url)
        self.assertIn('xl/worksheets/sheet1.xml', zipfile.ZipFile(io.BytesIO(wizard.xlsx_file.content)).namelist())

    def test_period_buttons_and_validation(self):
        wizard = self.wizard('ledger', date_to='2026-05-20')
        wizard.action_period_quarter()
        self.assertEqual((wizard.date_from, wizard.date_to),
                         (fields.Date.to_date('2026-04-01'), fields.Date.to_date('2026-06-30')))
        wizard.action_period_year()
        self.assertEqual(wizard.date_from, fields.Date.to_date('2026-01-01'))
        with self.assertRaises(UserError):
            wizard.date_from = '2027-01-01'

    def test_requires_accounting_group_and_company_access(self):
        user = self.env['res.users'].create({
            'name': 'Nhân viên thường', 'login': 'vn_plain_user', 'company_id': self.company.id,
            'company_ids': [Command.set(self.company.ids)],
            'group_ids': [Command.set(self.env.ref('base.group_user').ids)]})
        with self.assertRaises(AccessError):
            self.wizard('journal').with_user(user)._get_report_data()
