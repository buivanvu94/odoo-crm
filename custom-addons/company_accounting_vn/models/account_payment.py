from odoo import api, fields, models

from ..tools.vietnamese_converter import amount_to_words_vi, format_date_vi

NON_ACCOUNTING_TYPES = ('line_section', 'line_subsection', 'line_note')


class AccountPayment(models.Model):
    """Thông tin phiếu thu / phiếu chi.

    Không ghi đè action_post: việc chặn phiếu chi vượt hạn mức nằm ở company_payment_approval.
    """
    _inherit = 'account.payment'

    receiver_payer_name = fields.Char(
        string='Payer / Receiver Name', compute='_compute_receiver_payer', store=True,
        readonly=False, copy=False)
    receiver_payer_address = fields.Char(
        string='Payer / Receiver Address', compute='_compute_receiver_payer', store=True,
        readonly=False, copy=False)
    attached_documents = fields.Char(
        string='Attached Original Documents', copy=False,
        help='For example: 03 invoices with delivery notes.')

    @api.depends('partner_id')
    def _compute_receiver_payer(self):
        for payment in self:
            partner = payment.partner_id
            payment.receiver_payer_name = partner.name or False
            address = partner._display_address(without_name=True) if partner else ''
            payment.receiver_payer_address = ', '.join(filter(None, address.splitlines())) or False

    def _get_voucher_accounts(self):
        """Return (debit accounts, credit accounts) printed on the cash voucher.

        The posted entry is used when it exists. The clearing (outstanding) account is shown as
        the journal's own cash / bank account (111x / 112x) as accountants expect on a voucher.
        """
        self.ensure_one()
        self = self.with_company(self.company_id)  # account codes depend on the company of the payment
        outstanding = self.outstanding_account_id
        if self.move_id:
            lines = self.move_id.line_ids.filtered(lambda line: line.display_type not in NON_ACCOUNTING_TYPES)
            debit = lines.filtered(lambda line: line.debit > 0).account_id
            credit = lines.filtered(lambda line: line.credit > 0).account_id
        else:
            liquidity = outstanding or self.journal_id.default_account_id
            if self.payment_type == 'inbound':
                debit, credit = liquidity, self.destination_account_id
            else:
                debit, credit = self.destination_account_id, liquidity
        own_account = self.journal_id.default_account_id
        if outstanding and own_account and self.journal_id.type in ('cash', 'bank'):
            # Only the journal's own side: an internal transfer posts its other side to the same account
            # (transfer account = outstanding account), which must not be rewritten as the cash account too.
            if self.payment_type == 'inbound' and outstanding in debit:
                debit = (debit - outstanding) | own_account
            elif self.payment_type == 'outbound' and outstanding in credit:
                credit = (credit - outstanding) | own_account
        return debit, credit

    def _get_voucher_data(self):
        """Values shared by the 01-TT and 02-TT QWeb templates."""
        self.ensure_one()
        self = self.with_company(self.company_id)  # account codes depend on the company of the payment
        debit, credit = self._get_voucher_accounts()
        company_currency = self.company_id.currency_id
        # Payment amount only: write-off or discount lines of the entry are not cash received/paid.
        amount = abs(self.amount_company_currency_signed)
        return {
            'debit_codes': ', '.join(debit.mapped('vn_display_code')),
            'credit_codes': ', '.join(credit.mapped('vn_display_code')),
            'amount': amount,
            'currency': company_currency,
            'amount_words': amount_to_words_vi(amount) if company_currency.name == 'VND' else '',
            'date_text': format_date_vi(self.date),
        }
