"""Báo cáo tài chính TT 99: dữ liệu thật (bút toán + payment đã ghi sổ) rồi kiểm tra các đẳng thức kế toán."""
import io
import zipfile
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .vn_accounting_test_base import VNAccountingCommon

M = 1000000.0


@tagged('post_install', '-at_install')
class TestFinancialReports(VNAccountingCommon):

    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.prev_day = self.today.replace(day=1) - timedelta(days=1)  # cuối tháng trước
        self.manager = self._user('vn_fin_manager', 'account.group_account_manager')
        self.accountant = self._user('vn_fin_user', 'account.group_account_user')
        # Tháng trước: góp vốn 100tr (40tr tiền mặt, 60tr tiền gửi).
        self._entry(self.prev_day, [('111', 40 * M, 0), ('112', 60 * M, 0), ('411', 0, 100 * M)])
        # Tháng này: mua hàng trả tiền ngay, bán hàng ghi nợ KH, thu tiền qua payment, giá vốn, chi phí, lương,
        # vay, lãi vay, mua TSCĐ, khấu hao, chi phí thuế TNDN chưa nộp.
        self._entry(self.today, [('156', 20 * M, 0), ('133', 2 * M, 0), ('111', 0, 22 * M)])
        receivable = self.partner.with_company(self.company).property_account_receivable_id.code  # cùng TK với payment
        self._entry(self.today, [(receivable, 11 * M, 0, self.partner), ('511', 0, 10 * M), ('3331', 0, 1 * M)])
        self.payment = self.env['account.payment'].create({
            'payment_type': 'inbound', 'partner_type': 'customer', 'partner_id': self.partner.id,
            'amount': 11 * M, 'journal_id': self.cash_journal.id, 'date': self.today})
        self.payment.action_post()
        self._entry(self.today, [('632', 12 * M, 0), ('156', 0, 12 * M)])
        self._entry(self.today, [('642', 3 * M, 0), ('111', 0, 3 * M)])
        self._entry(self.today, [('642', 4 * M, 0), ('334', 0, 4 * M)])
        self._entry(self.today, [('334', 4 * M, 0), ('112', 0, 4 * M)])
        self._entry(self.today, [('112', 30 * M, 0), ('341', 0, 30 * M)])
        self._entry(self.today, [('635', 0.5 * M, 0), ('112', 0, 0.5 * M)])
        self._entry(self.today, [('211', 15 * M, 0), ('112', 0, 15 * M)])
        self._entry(self.today, [('642', 1 * M, 0), ('214', 0, 1 * M)])
        self._entry(self.today, [('821', 0.5 * M, 0), ('3334', 0, 0.5 * M)])

    # ------------------------------------------------------------------ tiện ích
    def _user(self, login, group_xmlid):
        return self.env['res.users'].create({
            'name': login, 'login': login, 'email': '%s@example.com' % login,
            'company_id': self.company.id, 'company_ids': [Command.set(self.company.ids)],
            'group_ids': [Command.set([self.env.ref('base.group_user').id, self.env.ref(group_xmlid).id])],
        })

    def _entry(self, date, lines):
        move = self.create_entry(lines, post=False)
        move.date = date
        move.action_post()
        return move

    def _wizard(self, **vals):
        vals = {'company_id': self.company.id, 'period_type': 'month', 'year': self.today.year,
                'month': str(self.today.month), **vals}
        return self.env['vn.financial.report.wizard'].with_user(self.manager).create(vals)

    def _values(self, wizard, key='value'):
        """``{(mẫu, mã số): giá trị}`` của mọi báo cáo wizard tính ra."""
        return {(section['form_code'], row['code']): row[key]
                for section in wizard._get_sections() for row in section['rows'] if row['code']}

    def _cash_balance(self):
        lines = self.env['account.move.line'].search([
            ('parent_state', '=', 'posted'), ('company_id', '=', self.company.id)])
        return sum(line.balance for line in lines if line.account_id.vn_display_code.startswith(('111', '112', '113')))

    # ------------------------------------------------------------------ B01
    def test_financial_position_balances(self):
        # Payment ghi vào TK trung gian 113x nhưng vẫn là tiền.
        self.assertTrue(self.payment.outstanding_account_id.vn_display_code.startswith('113'))
        values = self._values(self._wizard(report_type='b01'))
        self.assertEqual(values['B01-DN', '111'], 96.5 * M)
        self.assertEqual(values['B01-DN', '111'], self._cash_balance())
        self.assertEqual(values['B01-DN', '141'], 8 * M)
        self.assertEqual(values['B01-DN', '152'], 2 * M)
        self.assertEqual(values['B01-DN', '222'], 15 * M)
        self.assertEqual(values['B01-DN', '223'], -1 * M)
        self.assertEqual(values['B01-DN', '270'], 120.5 * M)
        self.assertEqual(values['B01-DN', '300'], 31.5 * M)
        self.assertEqual(values['B01-DN', '420'], -11 * M)  # kết quả kinh doanh chưa kết chuyển
        self.assertEqual(values['B01-DN', '270'], values['B01-DN', '440'])

    # ------------------------------------------------------------------ B02
    def test_income_statement(self):
        values = self._values(self._wizard(report_type='b02'))
        expected = {'01': 10 * M, '10': 10 * M, '11': 12 * M, '20': -2 * M, '22': 0.5 * M, '25': 8 * M,
                    '30': -10.5 * M, '50': -10.5 * M, '51': 0.5 * M, '60': -11 * M}
        for code, amount in expected.items():
            self.assertEqual(values['B02-DN', code], amount, 'B02 line %s' % code)

    def test_closing_entries_do_not_change_results(self):
        before = self._values(self._wizard())
        self._entry(self.today, [('511', 10 * M, 0), ('911', 0, 10 * M)])
        self._entry(self.today, [('911', 21 * M, 0), ('632', 0, 12 * M), ('642', 0, 8 * M),
                                 ('635', 0, 0.5 * M), ('821', 0, 0.5 * M)])
        self._entry(self.today, [('421', 11 * M, 0), ('911', 0, 11 * M)])
        after = self._values(self._wizard())
        self.assertEqual(after, before)
        self.assertEqual(after['B01-DN', '270'], after['B01-DN', '440'])

    # ------------------------------------------------------------------ B03
    def test_cash_flow_direct_ties_to_cash(self):
        values = self._values(self._wizard(report_type='b03', cash_flow_method='direct'))
        expected = {'01': 11 * M, '02': -25 * M, '03': -4 * M, '04': -0.5 * M, '05': 0.0, '20': -18.5 * M,
                    '21': -15 * M, '30': -15 * M, '31': 0.0, '33': 30 * M, '40': 30 * M, '50': -3.5 * M,
                    '60': 100 * M, '70': 96.5 * M}
        for code, amount in expected.items():
            self.assertEqual(values['B03-DN', code], amount, 'B03 line %s' % code)
        self.assertEqual(values['B03-DN', '70'], self._cash_balance())

    def test_cash_flow_indirect_matches_direct(self):
        direct = self._values(self._wizard(report_type='b03', cash_flow_method='direct'))
        indirect = self._values(self._wizard(report_type='b03', cash_flow_method='indirect'))
        self.assertEqual(indirect['B03-DN', '01'], -10.5 * M)
        for code in ('20', '30', '40', '50', '60', '70'):
            self.assertEqual(indirect['B03-DN', code], direct['B03-DN', code], 'B03 line %s' % code)
        self.assertEqual(indirect['B03-DN', '70'], self._cash_balance())

    def test_cash_flow_first_period_has_zero_opening(self):
        wizard = self._wizard(report_type='b03', period_type='custom', date_from=self.prev_day, date_to=self.today)
        values = self._values(wizard)
        self.assertEqual(values['B03-DN', '60'], 0.0)
        self.assertEqual(values['B03-DN', '31'], 100 * M)
        self.assertEqual(values['B03-DN', '70'], self._cash_balance())

    # ------------------------------------------------------------------ kỳ so sánh, kỳ, quyền
    def test_previous_period_comparison(self):
        wizard = self._wizard(compare_previous=True)
        prior = self._values(wizard, 'prior')
        self.assertEqual(prior['B01-DN', '111'], 100 * M)
        self.assertEqual(prior['B01-DN', '270'], 100 * M)
        self.assertEqual(prior['B01-DN', '270'], prior['B01-DN', '440'])
        self.assertEqual(prior['B02-DN', '60'], 0.0)
        self.assertEqual(prior['B03-DN', '31'], 100 * M)
        self.assertEqual(prior['B03-DN', '70'], 100 * M)
        # Số kỳ này nối tiếp số kỳ trước: tiền đầu kỳ này = tiền cuối kỳ trước.
        self.assertEqual(self._values(wizard)['B03-DN', '60'], prior['B03-DN', '70'])
        self.assertTrue(all(s['has_prior'] for s in wizard._get_sections()))
        self.assertFalse(any(s['has_prior'] for s in self._wizard()._get_sections()))

    def test_period_dates(self):
        wizard = self._wizard(period_type='quarter', year=2026, quarter='2')
        self.assertEqual((str(wizard.date_from), str(wizard.date_to)), ('2026-04-01', '2026-06-30'))
        self.assertEqual(tuple(map(str, wizard._previous_range())), ('2026-01-01', '2026-03-31'))
        wizard = self._wizard(period_type='year', year=2026)
        self.assertEqual((str(wizard.date_from), str(wizard.date_to)), ('2026-01-01', '2026-12-31'))
        wizard = self._wizard(period_type='custom', date_from='2026-03-10', date_to='2026-03-19')
        self.assertEqual(tuple(map(str, wizard._previous_range())), ('2026-02-28', '2026-03-09'))
        with self.assertRaises(ValidationError):
            self._wizard(period_type='custom', date_from='2026-03-10', date_to='2026-03-01')

    def test_only_account_manager_can_open(self):
        with self.assertRaises(AccessError):
            self.env['vn.financial.report.wizard'].with_user(self.accountant).create({'company_id': self.company.id})
        with self.assertRaises(AccessError):
            self.env['vn.financial.report'].with_user(self.accountant).build(
                'b01', self.company, self.today, self.today)

    def test_formula_syntax_is_validated(self):
        with self.assertRaises(ValidationError):
            self.env['vn.financial.report.line'].create({
                'report_type': 'b02', 'code': '99', 'name': 'x', 'formula': 'XX(111)'})
        with self.assertRaises(ValidationError):
            self.env['vn.financial.report.line'].create({
                'report_type': 'b02', 'code': '98', 'name': 'x', 'formula': 'DB(111'})

    # ------------------------------------------------------------------ in ấn / Excel
    def test_html_render_and_xlsx(self):
        wizard = self._wizard(compare_previous=True)
        html, _kind = self.env['ir.actions.report'].with_user(self.manager)._render_qweb_html(
            'company_accounting_vn.action_report_vn_financial', wizard.ids)
        html = html.decode() if isinstance(html, bytes) else html
        for text in ('BÁO CÁO TÌNH HÌNH TÀI CHÍNH', 'BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH', 'B03-DN', 'TỔNG CỘNG TÀI SẢN'):
            self.assertIn(text, html)
        action = wizard.action_export_xlsx()
        attachment_id = int(action['url'].split('/web/content/')[1].split('?')[0])
        content = self.env['ir.attachment'].browse(attachment_id).raw
        with zipfile.ZipFile(io.BytesIO(content)) as book:
            self.assertEqual(sum(n.startswith('xl/worksheets/sheet') for n in book.namelist()), 3)
