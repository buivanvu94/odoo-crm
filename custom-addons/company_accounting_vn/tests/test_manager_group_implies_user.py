"""Kế toán trưởng (account.group_account_manager) phải dùng được sổ sách dành cho nhóm user."""
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestManagerImpliesUser(TransactionCase):

    def test_manager_can_use_ledger_wizard(self):
        manager = self.env['res.users'].create({
            'name': 'VN Manager', 'login': 'vn_mgr_implied',
            'group_ids': [Command.set([self.env.ref('base.group_user').id,
                                       self.env.ref('account.group_account_manager').id])],
        })
        self.assertTrue(manager.has_group('account.group_account_user'))
        wizard = self.env['accounting.report.wizard'].with_user(manager).create({'report_type': 'journal'})
        wizard.action_view_screen()
