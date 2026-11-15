from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    counterpart_account_id = fields.Many2one(
        'account.account', string='Counterpart Account', copy=False, index='btree_not_null',
        ondelete='set null',
        help='Opposite-side account when it is unique (Nợ TK / Có TK). Empty when several accounts match.')
    counterpart_name = fields.Char(
        string='Counterpart Codes', copy=False,
        help='Comma-separated codes of every opposite-side account matched to this line.')
