"""Nền chung cho test sổ kế toán: dữ liệu bút toán thật của tháng 1 và tháng 2/2026."""
from odoo import Command

from .vn_accounting_test_base import VNAccountingCommon

JAN, FEB = '2026-01-15', '2026-02-10'


class LedgerCommon(VNAccountingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.accountant = cls.env['res.users'].create({
            'name': 'Kế toán sổ sách', 'login': 'vn_ledger_accountant', 'company_id': cls.company.id,
            'company_ids': [Command.set(cls.company.ids)],
            'group_ids': [Command.set(cls.env.ref('account.group_account_user').ids)]})
        cls.partner2 = cls.env['res.partner'].create({'name': 'Nhà cung cấp Test'})
        # Kỳ trước: góp vốn 1.000.000 bằng tiền mặt. Trong kỳ (tháng 2): bán chịu, thu nợ, mua chịu.
        cls.entry(JAN, [('111', 1000000, 0), ('411', 0, 1000000)])
        cls.entry(FEB, [('131', 500000, 0, cls.partner), ('511', 0, 500000)])
        cls.entry(FEB, [('111', 300000, 0), ('131', 0, 300000, cls.partner)])
        cls.entry(FEB, [('156', 200000, 0), ('331', 0, 200000, cls.partner2)])
        cls.draft = cls.entry(FEB, [('111', 999, 0), ('411', 0, 999)], post=False)

    @classmethod
    def entry(cls, date, lines, post=True):
        move = cls.env['account.move'].create({
            'move_type': 'entry', 'journal_id': cls.misc_journal.id, 'date': date,
            'line_ids': [Command.create({
                'name': 'dòng %s' % code, 'account_id': cls.account(code).id, 'debit': debit, 'credit': credit,
                'partner_id': (rest[0].id if rest else False),
            }) for code, debit, credit, *rest in lines],
        })
        if post:
            move.action_post()
        return move

    def wizard(self, report_type, date_from='2026-02-01', date_to='2026-02-28', **extra):
        return self.env['accounting.report.wizard'].with_user(self.accountant).create({
            'company_id': self.company.id, 'report_type': report_type,
            'date_from': date_from, 'date_to': date_to, **extra})

    def rows(self, report_type, **kwargs):
        return self.wizard(report_type, **kwargs)._get_report_data()['rows']

    @staticmethod
    def section(rows, label_part):
        """Các dòng của nhóm có nhãn chứa label_part (tới nhóm kế tiếp)."""
        start = next(i for i, r in enumerate(rows) if r['kind'] == 'group' and label_part in r['label'])
        end = next((i for i in range(start + 1, len(rows)) if rows[i]['kind'] in ('group', 'grand')), len(rows))
        return rows[start:end]
