from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError

NON_ACCOUNTING_TYPES = ('line_section', 'line_subsection', 'line_note')
# The partner rule on 131/331/141 only applies to companies using a Vietnamese chart.
VN_CHART_TEMPLATES = ('vn', 'vn_tt99')


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------------------------------------------------------
    # Posting / resetting
    # ------------------------------------------------------------------
    def _post(self, soft=True):
        """Hook for every posting route (action_post, payments, auto-post)."""
        drafts = self.filtered(lambda move: move.state == 'draft')
        drafts._check_partner_required_accounts()
        posted = super()._post(soft=soft)
        (drafts & posted)._compute_counterpart_accounts()
        return posted

    def button_draft(self):
        res = super().button_draft()
        self.line_ids.write({'counterpart_account_id': False, 'counterpart_name': False})
        return res

    def _check_partner_required_accounts(self):
        """Block posting when 131/331/141 lines have no partner (Vietnamese charts only)."""
        for move in self:
            if move.company_id.root_id.chart_template not in VN_CHART_TEMPLATES:
                continue
            # Mã TK phụ thuộc công ty: đọc theo công ty của bút toán, không theo công ty đang hoạt động.
            move = move.with_company(move.company_id)
            lines = move.line_ids.filtered(
                lambda line: line.display_type not in NON_ACCOUNTING_TYPES
                and line.account_id.vn_partner_required
                and not line.partner_id
                and not line.company_currency_id.is_zero(line.balance))
            if lines:
                raise UserError(_(
                    "Journal entry %(move)s: accounts %(accounts)s require a partner on every line.",
                    move=move.display_name,
                    accounts=', '.join(sorted(set(lines.account_id.mapped('vn_display_code')))),
                ))

    # ------------------------------------------------------------------
    # Counterpart accounts (Nợ TK / Có TK)
    # ------------------------------------------------------------------
    def _compute_counterpart_accounts(self):
        """Assign the opposite-side accounts to every line of the entries.

        1 debit - 1 credit, 1 - n and n - 1: every line is matched to all the lines on
        the opposite side. n - n: see ``_match_complex_counterparts``.
        """
        for move in self:
            move = move.with_company(move.company_id)
            lines = move.line_ids.filtered(lambda line: line.display_type not in NON_ACCOUNTING_TYPES)
            order = lambda line: (line.sequence, line.id)  # noqa: E731
            debits = lines.filtered(lambda line: line.debit > 0).sorted(order)
            credits = lines.filtered(lambda line: line.credit > 0).sorted(order)
            if len(debits) > 1 and len(credits) > 1:
                matches = move._match_complex_counterparts(debits, credits)
            else:
                matches = {line: credits.account_id for line in debits}
                matches.update({line: debits.account_id for line in credits})
            move._write_counterparts(lines, matches)

    def _match_complex_counterparts(self, debit_lines, credit_lines):
        """n debit - n credit: sequential allocation of debit amounts onto credit amounts.

        Each debit line consumes the credit lines in order until its amount is exhausted,
        so a line is only paired with the opposite lines that actually share its value.
        Returns ``{line: account.account recordset}``.
        """
        self.ensure_one()
        currency = self.company_currency_id
        matches = defaultdict(lambda: self.env['account.account'])
        debit_left = [line.debit for line in debit_lines]
        credit_left = [line.credit for line in credit_lines]
        i = j = 0
        while i < len(debit_lines) and j < len(credit_lines):
            taken = min(debit_left[i], credit_left[j])
            if taken > 0:
                matches[debit_lines[i]] |= credit_lines[j].account_id
                matches[credit_lines[j]] |= debit_lines[i].account_id
            debit_left[i] -= taken
            credit_left[j] -= taken
            if currency.is_zero(debit_left[i]):
                i += 1
            if currency.is_zero(credit_left[j]):
                j += 1
        # Unbalanced leftovers (rounding): fall back to every opposite account.
        for line in debit_lines:
            matches.setdefault(line, credit_lines.account_id)
        for line in credit_lines:
            matches.setdefault(line, debit_lines.account_id)
        return matches

    def _write_counterparts(self, lines, matches):
        """Persist ``matches``; lines without a match are cleared. One write per distinct value."""
        self.ensure_one()
        grouped = defaultdict(lambda: self.env['account.move.line'])
        for line in lines:
            accounts = matches.get(line, self.env['account.account'])
            name = ', '.join(dict.fromkeys(accounts.mapped('vn_display_code'))) or False
            account_id = accounts.id if len(accounts) == 1 else False
            grouped[(account_id, name)] |= line
        for (account_id, name), group in grouped.items():
            group.write({'counterpart_account_id': account_id, 'counterpart_name': name})
