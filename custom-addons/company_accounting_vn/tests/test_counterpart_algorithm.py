from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .vn_accounting_test_base import VNAccountingCommon


@tagged('post_install', '-at_install')
class TestCounterpartAlgorithm(VNAccountingCommon):

    def line(self, move, code):
        return move.line_ids.filtered(lambda line: line.account_id == self.account(code))

    def test_one_debit_one_credit(self):
        move = self.create_entry([('156', 100, 0), ('111', 0, 100)])
        debit, credit = self.line(move, '156'), self.line(move, '111')
        self.assertEqual(debit.counterpart_account_id, self.account('111'))
        self.assertEqual(debit.counterpart_name, '111')
        self.assertEqual(credit.counterpart_account_id, self.account('156'))
        self.assertEqual(credit.counterpart_name, '156')

    def test_one_debit_many_credits(self):
        move = self.create_entry([('156', 100, 0), ('111', 0, 60), ('112', 0, 40)])
        debit = self.line(move, '156')
        self.assertFalse(debit.counterpart_account_id)
        self.assertEqual(debit.counterpart_name, '111, 112')
        for code in ('111', '112'):
            self.assertEqual(self.line(move, code).counterpart_account_id, self.account('156'))

    def test_many_debits_one_credit(self):
        move = self.create_entry([('156', 60, 0), ('1331', 40, 0), ('331', 0, 100, self.partner)])
        credit = self.line(move, '331')
        self.assertFalse(credit.counterpart_account_id)
        self.assertEqual(credit.counterpart_name, '156, 1331')
        for code in ('156', '1331'):
            self.assertEqual(self.line(move, code).counterpart_account_id, self.account('331'))

    def test_many_debits_many_credits_sequential(self):
        move = self.create_entry([
            ('156', 100, 0), ('152', 50, 0), ('111', 0, 70), ('112', 0, 80)])
        expected = {
            '156': '111, 112',  # 70 from 111 then 30 from 112
            '152': '112',  # the remaining 50 of 112
            '111': '156',
            '112': '156, 152',
        }
        for code, names in expected.items():
            self.assertEqual(self.line(move, code).counterpart_name, names, code)
        self.assertEqual(self.line(move, '152').counterpart_account_id, self.account('112'))
        self.assertFalse(self.line(move, '156').counterpart_account_id)

    def test_draft_clears_and_repost_recomputes(self):
        move = self.create_entry([('156', 100, 0), ('111', 0, 100)])
        move.button_draft()
        self.assertFalse(move.line_ids.counterpart_account_id)
        self.assertFalse(any(move.line_ids.mapped('counterpart_name')))
        move.action_post()
        self.assertEqual(self.line(move, '156').counterpart_name, '111')

    def test_partner_required_accounts(self):
        for code, side in (('131', (100, 0)), ('331', (0, 100)), ('141', (100, 0))):
            other = ('111', side[1], side[0])
            with self.subTest(account=code):
                with self.assertRaises(UserError):
                    self.create_entry([(code, *side), other])
        move = self.create_entry([('131', 100, 0, self.partner), ('511', 0, 100)])
        self.assertEqual(move.state, 'posted')

    def test_customer_invoice(self):
        tax = self.env['account.tax'].search([
            ('company_id', '=', self.company.id), ('type_tax_use', '=', 'sale'), ('amount', '=', 10.0),
            ('amount_type', '=', 'percent')], limit=1)
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({
                'name': 'Hàng hóa', 'quantity': 1, 'price_unit': 1000000, 'tax_ids': [Command.set(tax.ids)],
            })],
        })
        invoice.action_post()
        receivable = invoice.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        others = invoice.line_ids - receivable
        self.assertEqual(len(receivable), 1)
        self.assertEqual(len(others), 2)
        self.assertEqual(set(others.counterpart_account_id.ids), set(receivable.account_id.ids))
        self.assertEqual(
            set(receivable.counterpart_name.split(', ')), set(others.account_id.mapped('vn_display_code')))
