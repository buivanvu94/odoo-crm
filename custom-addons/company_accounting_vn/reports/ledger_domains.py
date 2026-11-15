"""Bộ lọc (domain) dùng chung cho các sổ kế toán của ``vn.ledger.engine``.

Mã tài khoản phụ thuộc công ty: mọi hàm ở đây phải chạy trong ngữ cảnh công ty của wizard
(``vn.ledger.engine.build`` đã bảo đảm điều đó).
"""
from odoo import api, models

from .ledger_layout import BOOK_PREFIX


class VNLedgerDomains(models.AbstractModel):
    _inherit = 'vn.ledger.engine'

    @api.model
    def _base_domain(self, wizard):
        domain = [('company_id', '=', wizard.company_id.id), ('parent_state', '=', 'posted')]
        if wizard.partner_ids:
            domain.append(('partner_id', 'in', wizard.partner_ids.ids))
        if wizard.journal_ids:
            domain.append(('journal_id', 'in', wizard.journal_ids.ids))
        return domain

    @api.model
    def _accounts_by_prefix(self, company, prefixes):
        """Tài khoản theo mã hiển thị (mã 1110 thuộc tiền tố 111, 1121 thuộc 112)."""
        code_domain = [('code', '=like', prefix + '%') for prefix in prefixes]
        domain = ['|'] * (len(code_domain) - 1) + code_domain + [('company_ids', 'in', company.id)]
        return self.env['account.account'].search(domain)

    @api.model
    def _account_domain(self, wizard):
        """Bộ lọc TK của wizard: chọn TK cha thì lấy luôn các TK con cùng tiền tố."""
        if not wizard.account_ids:
            return []
        prefixes = list({a.vn_display_code for a in wizard.account_ids})
        return [('account_id', 'in', self._accounts_by_prefix(wizard.company_id, prefixes).ids)]

    @api.model
    def _outstanding_accounts(self, company, journals):
        """TK trung gian mà ``account.payment`` ghi vào thay cho TK tiền của sổ nhật ký.

        Khi payment method line chưa khai báo, Odoo dùng TK mặc định của chart hoặc TK chuyển tiền
        của công ty (với l10n_vn đó là 1131 cho cả tiền mặt lẫn ngân hàng).
        """
        template = self.env['account.chart.template'].with_context(allowed_company_ids=company.root_id.ids)
        outstanding = self.env['account.account']
        for ref in ('account_journal_payment_debit_account_id', 'account_journal_payment_credit_account_id'):
            outstanding |= template.ref(ref, raise_if_not_found=False) or company.transfer_account_id
        for journal in journals:
            outstanding |= journal._get_journal_inbound_outstanding_payment_accounts()
            outstanding |= journal._get_journal_outbound_outstanding_payment_accounts()
        return outstanding

    @api.model
    def _cash_bank_domain(self, wizard, kind):
        """Sổ quỹ / sổ tiền gửi = dòng của TK 111 / 112 CỘNG dòng TK trung gian của payment thuộc đúng
        các sổ nhật ký loại ``kind``.

        * TK treo (suspense) và TK trung gian (outstanding) của mọi sổ nhật ký tiền / ngân hàng bị loại khỏi
          TK chính, kể cả khi mã của chúng nằm trong tiền tố 111 / 112 (ví dụ l10n_vn: TK treo là 1121).
        * Dòng TK trung gian của payment luôn được tính ở ngày payment (nên số dư không đổi khi đối soát sau).
        * Dòng sao kê (TK chính) mà bút toán của nó có vế TK trung gian đã khớp với payment tới hết
          ``date_to`` thì bị loại: số tiền đó đã nằm ở dòng payment. Khớp sau ``date_to`` thì chưa loại,
          nên sổ của kỳ đã đóng không đổi theo thời điểm in. Khớp một phần cũng loại cả dòng sao kê.
        """
        company = wizard.company_id
        cash_bank_journals = self.env['account.journal'].search([
            ('company_id', '=', company.id), ('type', 'in', ('cash', 'bank'))])
        journals = cash_bank_journals.filtered(lambda journal: journal.type == kind)
        all_outstanding = self._outstanding_accounts(company, cash_bank_journals)
        main = self._accounts_by_prefix(company, [BOOK_PREFIX[kind]])
        main -= company._vn_suspense_accounts() | all_outstanding
        cleared = ('move_id', 'any', [('line_ids', 'any', [
            ('account_id', 'in', all_outstanding.ids), '|',
            ('matched_debit_ids.max_date', '<=', wizard.date_to),
            ('matched_credit_ids.max_date', '<=', wizard.date_to)])])
        outstanding = self._outstanding_accounts(company, journals)
        return ['|', '&', ('account_id', 'in', main.ids), '!', cleared,
                '&', ('account_id', 'in', outstanding.ids), ('payment_id.journal_id', 'in', journals.ids)]
