"""Nền cho test đa công ty: công ty B có chart vn_tt99, người dùng đứng ở công ty A (công ty đang hoạt động)."""
from odoo import Command

from .vn_accounting_test_base import VNAccountingCommon


class MultiCompanyCommon(VNAccountingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.company_a = cls.company
        cls.company_b = env['res.company'].create({
            'name': 'VN TT99 Test Company B', 'country_id': env.ref('base.vn').id,
            'currency_id': cls.company_a.currency_id.id})
        env.user.company_ids |= cls.company_b
        env['account.chart.template'].with_context(allowed_company_ids=cls.company_b.ids).try_loading(
            'vn_tt99', company=cls.company_b, install_demo=False)
        cls.company_b.payment_approval_enabled = False
        cls.accountant = env['res.users'].create({
            'name': 'Kế toán hai công ty', 'login': 'vn_two_company_accountant',
            'company_id': cls.company_a.id, 'company_ids': [Command.set((cls.company_a | cls.company_b).ids)],
            'group_ids': [Command.set(env.ref('account.group_account_user').ids)]})
        # Công ty đang hoạt động là A (đứng đầu allowed_company_ids), sổ cần lập cho công ty B.
        cls.env_a = env(context=dict(env.context, allowed_company_ids=[cls.company_a.id, cls.company_b.id]))

    def account_of(self, company, code):
        code = code if len(code) > 3 else code.ljust(4, '0')
        account = self.env_a['account.account'].with_company(company).search([
            ('code', '=', code), ('company_ids', 'in', company.id)], limit=1)
        self.assertTrue(account, 'Account %s not found in %s' % (code, company.name))
        return account

    def entry_of(self, company, lines, date='2026-02-10', post=True):
        """Bút toán của ``company`` tạo và đăng sổ khi người dùng đang đứng ở công ty A."""
        journal = self.env_a['account.journal'].search([
            ('company_id', '=', company.id), ('type', '=', 'general')], limit=1)
        move = self.env_a['account.move'].with_company(company).create({
            'move_type': 'entry', 'journal_id': journal.id, 'date': date,
            'line_ids': [Command.create({
                'name': code, 'account_id': self.account_of(company, code).id, 'debit': debit, 'credit': credit,
                'partner_id': (rest[0].id if rest else False),
            }) for code, debit, credit, *rest in lines]})
        if post:
            move.with_company(self.company_a).action_post()
        return move
