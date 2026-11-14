from odoo import fields, models

MONEY_FIELDS = ['debit', 'credit', 'bal_debit', 'bal_credit', 'open_debit', 'open_credit',
                'close_debit', 'close_credit']


class AccountingReportLine(models.TransientModel):
    """Dòng kết quả tạm của sổ, dùng để xem trên màn hình (list view có phân trang)."""
    _name = 'accounting.report.line'
    _description = 'Accounting report result line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('accounting.report.wizard', required=True, ondelete='cascade', index=True)
    currency_id = fields.Many2one(related='wizard_id.company_id.currency_id')
    sequence = fields.Integer()
    kind = fields.Selection([
        ('line', 'Line'), ('group', 'Group'), ('open', 'Opening'), ('total', 'Total'),
        ('close', 'Closing'), ('grand', 'Grand total')], required=True)
    date = fields.Char()
    voucher = fields.Char()
    label = fields.Char(string='Description')
    account = fields.Char()
    counterpart = fields.Char(string='Counterpart')
    partner = fields.Char()
    journal = fields.Char()
    debit = fields.Monetary()
    credit = fields.Monetary()
    bal_debit = fields.Monetary(string='Balance Debit')
    bal_credit = fields.Monetary(string='Balance Credit')
    open_debit = fields.Monetary(string='Opening Debit')
    open_credit = fields.Monetary(string='Opening Credit')
    close_debit = fields.Monetary(string='Closing Debit')
    close_credit = fields.Monetary(string='Closing Credit')
