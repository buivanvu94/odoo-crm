"""Backfill đối ứng, quyền truy cập wizard tạm, thứ tự chữ ký và thành tiền phiếu kho."""
from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.company_accounting_vn.hooks import backfill_counterparts

from .vn_accounting_test_base import VNAccountingCommon


@tagged('post_install', '-at_install')
class TestBackfillCounterparts(VNAccountingCommon):

    def test_backfill_restores_counterparts_in_batches_and_is_idempotent(self):
        simple = self.create_entry([('111', 100000, 0), ('411', 0, 100000)])
        multi = self.create_entry([('111', 60000, 0), ('112', 40000, 0), ('411', 0, 70000), ('511', 0, 30000)])
        moves = simple | multi

        def snapshot():
            return {line.id: (line.counterpart_name, line.counterpart_account_id.id, line.balance)
                    for line in moves.line_ids}

        expected = snapshot()
        self.assertTrue(all(name for name, _acc, _bal in expected.values()))
        moves.line_ids.write({'counterpart_account_id': False, 'counterpart_name': False})
        backfill_counterparts(self.env, batch_size=1)
        self.assertEqual(snapshot(), expected)
        backfill_counterparts(self.env, batch_size=1)
        self.assertEqual(snapshot(), expected)
        self.assertEqual(set(moves.mapped('state')), {'posted'})

    def test_backfill_only_touches_posted_moves_missing_a_counterpart(self):
        missing = self.create_entry([('111', 100000, 0), ('411', 0, 100000)])
        complete = self.create_entry([('111', 50000, 0), ('411', 0, 50000)])
        draft = self.create_entry([('111', 70000, 0), ('411', 0, 70000)], post=False)
        missing.line_ids.write({'counterpart_account_id': False, 'counterpart_name': False})
        complete.line_ids.write({'counterpart_name': 'đã có'})  # giá trị giữ nguyên: bút toán này không bị tính lại
        backfill_counterparts(self.env, batch_size=1)
        self.assertEqual(set(missing.line_ids.mapped('counterpart_name')), {'411', '111'})
        self.assertEqual(set(complete.line_ids.mapped('counterpart_name')), {'đã có'})
        self.assertFalse(any(draft.line_ids.mapped('counterpart_name')))


@tagged('post_install', '-at_install')
class TestReportAccess(VNAccountingCommon):

    def _user(self, login, group_xmlid):
        return self.env['res.users'].create({
            'name': login, 'login': login, 'company_id': self.company.id,
            'company_ids': [Command.set(self.company.ids)],
            'group_ids': [Command.set([self.env.ref('base.group_user').id, self.env.ref(group_xmlid).id])]})

    def test_ledger_wizard_and_lines_are_private_to_their_creator(self):
        user_a = self._user('vn_acc_a', 'account.group_account_user')
        user_b = self._user('vn_acc_b', 'account.group_account_user')
        self.create_entry([('111', 5000, 0), ('411', 0, 5000)])
        wizard = self.env['accounting.report.wizard'].with_user(user_a).create({
            'company_id': self.company.id, 'report_type': 'journal',
            'date_from': '2020-01-01', 'date_to': '2099-12-31'})
        wizard.action_view_screen()
        self.assertTrue(wizard.line_ids)
        as_b = self.env['accounting.report.wizard'].with_user(user_b)
        self.assertFalse(as_b.search([('id', '=', wizard.id)]))
        self.assertFalse(self.env['accounting.report.line'].with_user(user_b).search([('wizard_id', '=', wizard.id)]))
        with self.assertRaises(AccessError):
            as_b.browse(wizard.id).read(['report_type'])
        with self.assertRaises(AccessError):
            as_b.browse(wizard.id)._get_report_data()
        self.assertEqual(wizard.with_user(user_a).line_ids, wizard.line_ids)  # chủ sở hữu vẫn đọc được

    def test_financial_wizard_and_excel_attachment_are_private(self):
        manager_a = self._user('vn_mgr_a', 'account.group_account_manager')
        manager_b = self._user('vn_mgr_b', 'account.group_account_manager')
        wizard = self.env['vn.financial.report.wizard'].with_user(manager_a).create({'company_id': self.company.id})
        action = wizard.action_export_xlsx()
        attachment_id = int(action['url'].split('/web/content/')[1].split('?')[0])
        self.assertTrue(self.env['ir.attachment'].with_user(manager_a).browse(attachment_id).raw)
        self.assertFalse(self.env['vn.financial.report.wizard'].with_user(manager_b).search([('id', '=', wizard.id)]))
        with self.assertRaises(AccessError):
            self.env['ir.attachment'].with_user(manager_b).browse(attachment_id).raw  # noqa: B018
