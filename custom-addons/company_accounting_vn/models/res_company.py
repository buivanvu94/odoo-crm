from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    accounting_regime = fields.Selection(
        selection=[
            ('tt99', 'Circular 99/2025/TT-BTC'),
            ('tt133', 'Circular 133/2016/TT-BTC'),
        ],
        string='Accounting Regime',
        default='tt99',
        required=True,
        help='Vietnamese accounting regime applied by this company.',
    )

    def _vn_suspense_accounts(self):
        """TK treo (suspense) của các sổ nhật ký tiền / ngân hàng và TK treo mặc định của công ty.

        Là vế đối ứng tạm của dòng sao kê chưa đối soát, không phải tiền (l10n_vn: 1121).
        """
        self.ensure_one()
        journals = self.env['account.journal'].search([('company_id', '=', self.id), ('type', 'in', ('cash', 'bank'))])
        return journals.suspense_account_id | self.account_journal_suspense_account_id
