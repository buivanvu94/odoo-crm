"""Báo cáo tài chính: tương đương tiền, công nợ theo đối tượng, dòng tiền theo bút toán, giảm trừ doanh thu."""
from datetime import timedelta

from odoo import Command, fields
from odoo.tests import tagged

from .vn_accounting_test_base import VNAccountingCommon


@tagged('post_install', '-at_install')
class TestFinancialReviewFixes(VNAccountingCommon):

    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.prev_day = self.today.replace(day=1) - timedelta(days=1)
        self.manager = self.env['res.users'].create({
            'name': 'vn_fix_manager', 'login': 'vn_fix_manager', 'company_id': self.company.id,
            'company_ids': [Command.set(self.company.ids)],
            'group_ids': [Command.set([self.env.ref('base.group_user').id,
                                       self.env.ref('account.group_account_manager').id])]})
        self.partner2 = self.env['res.partner'].create({'name': 'Khách trả trước'})
        self._entry(self.prev_day, [('111', 1000000, 0), ('411', 0, 1000000)])

    def _entry(self, date, lines):
        move = self.create_entry(lines, post=False)
        move.date = date
        move.action_post()
        return move

    def _values(self, report_type):
        wizard = self.env['vn.financial.report.wizard'].with_user(self.manager).create({
            'company_id': self.company.id, 'period_type': 'month', 'year': self.today.year,
            'month': str(self.today.month), 'report_type': report_type})
        return {(s['form_code'], row['code']): row['value']
                for s in wizard._get_sections() for row in s['rows'] if row['code']}

    def test_cash_equivalents_are_the_same_in_b01_and_b03(self):
        self._entry(self.today, [('12811', 200000, 0), ('111', 0, 200000)])  # gửi kỳ hạn <= 3 tháng
        b01 = self._values('b01')
        b03 = self._values('b03')
        self.assertEqual(b01['B01-DN', '110'], 1000000.0)
        self.assertEqual(b01['B01-DN', '112'], 200000.0)
        self.assertEqual(b03['B03-DN', '70'], b01['B01-DN', '110'])
        self.assertEqual(b03['B03-DN', '60'], 1000000.0)
        self.assertEqual(b03['B03-DN', '23'], 0.0)  # chuyển tiền sang tương đương tiền không phải chi đầu tư
        self.assertEqual(b01['B01-DN', '270'], b01['B01-DN', '440'])

    def test_receivables_are_netted_per_partner_not_per_account(self):
        self._entry(self.today, [('131', 100000, 0, self.partner), ('511', 0, 100000)])
        self._entry(self.today, [('111', 30000, 0), ('131', 0, 30000, self.partner2)])  # khách khác trả trước
        values = self._values('b01')
        self.assertEqual(values['B01-DN', '131'], 100000.0)
        self.assertEqual(values['B01-DN', '312'], 30000.0)
        self.assertEqual(values['B01-DN', '270'], values['B01-DN', '440'])

    def test_payables_are_netted_per_partner(self):
        self._entry(self.today, [('156', 80000, 0), ('331', 0, 80000, self.partner)])
        self._entry(self.today, [('331', 20000, 0, self.partner2), ('111', 0, 20000)])  # trả trước cho NCC khác
        values = self._values('b01')
        self.assertEqual(values['B01-DN', '311'], 80000.0)
        self.assertEqual(values['B01-DN', '132'], 20000.0)

    def test_cash_flow_does_not_offset_receipts_and_payments_of_same_account(self):
        self._entry(self.today, [('111', 100000, 0), ('131', 0, 100000, self.partner)])  # thu tiền khách
        self._entry(self.today, [('131', 50000, 0, self.partner), ('111', 0, 50000)])  # hoàn tiền cho khách
        values = self._values('b03')
        self.assertEqual(values['B03-DN', '01'], 100000.0)
        self.assertEqual(values['B03-DN', '07'], -50000.0)
        self.assertEqual(values['B03-DN', '70'], 1050000.0)

    def test_revenue_deductions_and_income_tax_split(self):
        self._entry(self.today, [('131', 100000, 0, self.partner), ('511', 0, 100000)])
        self._entry(self.today, [('511', 20000, 0), ('131', 0, 20000, self.partner)])  # credit note ghi Nợ thẳng 511
        self._entry(self.today, [('521', 5000, 0), ('131', 0, 5000, self.partner)])
        self._entry(self.today, [('8211', 7000, 0), ('3334', 0, 7000)])
        self._entry(self.today, [('8212', 3000, 0), ('243', 0, 3000)])
        values = self._values('b02')
        self.assertEqual(values['B02-DN', '01'], 100000.0)
        self.assertEqual(values['B02-DN', '02'], 25000.0)
        self.assertEqual(values['B02-DN', '10'], 75000.0)
        self.assertEqual(values['B02-DN', '51'], 7000.0)
        self.assertEqual(values['B02-DN', '52'], 3000.0)
        self.assertEqual(values['B02-DN', '60'], 75000.0 - 10000.0)
