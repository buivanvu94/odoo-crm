"""Nền chung cho test: một công ty VN dùng chart template ``vn_tt99``."""
from odoo import Command, fields
from odoo.tests.common import TransactionCase


class VNAccountingCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        vnd = cls.env.ref('base.VND')
        vnd.active = True
        cls.company = cls.env['res.company'].create({
            'name': 'VN TT99 Test Company',
            'country_id': cls.env.ref('base.vn').id,
            'currency_id': vnd.id,
        })
        cls.env.user.company_ids |= cls.company
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))
        cls.env['account.chart.template'].try_loading('vn_tt99', company=cls.company, install_demo=False)
        # Approval limits are exercised in a dedicated test.
        cls.company.payment_approval_enabled = False
        cls.misc_journal = cls.env['account.journal'].search([
            ('company_id', '=', cls.company.id), ('type', '=', 'general')], limit=1)
        cls.cash_journal = cls.env['account.journal'].search([
            ('company_id', '=', cls.company.id), ('type', '=', 'cash')], limit=1)
        cls.partner = cls.env['res.partner'].create({
            'name': 'Khách hàng Test', 'street': '1 Lê Lợi', 'city': 'Hà Nội'})

    @classmethod
    def account(cls, code):
        """Template codes are zero-padded to 4 digits, so 111 is stored as 1110."""
        code = code if len(code) > 3 else code.ljust(4, '0')
        account = cls.env['account.account'].search([('code', '=', code)], limit=1)
        assert account, 'Account %s not found' % code
        return account

    def create_entry(self, lines, post=True):
        """``lines``: iterable of (code, debit, credit[, partner])."""
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.misc_journal.id,
            'date': fields.Date.today(),
            'line_ids': [Command.create({
                'name': 'line %s' % code,
                'account_id': self.account(code).id,
                'debit': debit,
                'credit': credit,
                'partner_id': (rest[0].id if rest else False),
            }) for code, debit, credit, *rest in lines],
        })
        if post:
            move.action_post()
        return move
