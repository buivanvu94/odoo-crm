from odoo import api, fields, models

# Tài khoản phải chi tiết theo đối tượng (khách hàng / nhà cung cấp / người tạm ứng).
PARTNER_REQUIRED_PREFIXES = ('131', '331', '141')

ACCOUNT_CLASSES = [
    ('1', 'Class 1 - Short-term assets'),
    ('2', 'Class 2 - Long-term assets'),
    ('3', 'Class 3 - Liabilities'),
    ('4', 'Class 4 - Equity'),
    ('5', 'Class 5 - Revenue'),
    ('6', 'Class 6 - Production and business costs'),
    ('7', 'Class 7 - Other income'),
    ('8', 'Class 8 - Other expenses'),
    ('9', 'Class 9 - Income summary'),
]


class AccountAccount(models.Model):
    _inherit = 'account.account'

    vn_account_class = fields.Selection(
        ACCOUNT_CLASSES, string='VN Account Class', compute='_compute_vn_account_attributes')
    vn_partner_required = fields.Boolean(
        string='Partner Required', compute='_compute_vn_account_attributes',
        help='Journal items on this account must carry a partner (accounts 131, 331, 141).')
    vn_display_code = fields.Char(
        string='VN Display Code', compute='_compute_vn_account_attributes',
        help='Account code without the zero padding added by the chart template (1110 -> 111).')

    # Mã tài khoản phụ thuộc công ty (code_store là company_dependent) nên kết quả cũng vậy.
    @api.depends_context('company')
    @api.depends('code')
    def _compute_vn_account_attributes(self):
        valid_classes = {key for key, _label in ACCOUNT_CLASSES}
        for account in self:
            code = account.code or ''
            account.vn_account_class = code[:1] if code[:1] in valid_classes else False
            account.vn_partner_required = code.startswith(PARTNER_REQUIRED_PREFIXES)
            # Template codes are right-padded with zeros to 4 digits (111 -> 1110).
            account.vn_display_code = code[:3] if len(code) == 4 and code.endswith('0') else code
