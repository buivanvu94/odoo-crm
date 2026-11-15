"""Chart template ``vn_tt99``: dữ liệu của ``vn`` (l10n_vn) cộng chỉnh sửa theo TT 99/2025/TT-BTC.

l10n_vn (Odoo 20) đã có đúng 71 tài khoản cấp 1 của TT 99 (có 215, 332, 8212; không có 161, 417,
441, 461, 466, 611, 631) cùng nhóm thuế/thuế GTGT 0/5/8/10, không chịu thuế (KCT) và KKKTT.
Template này kế thừa ``vn`` và chỉ ghi đè phần khác biệt, không nhân bản dữ liệu.
"""
from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('vn_tt99')
    def _get_vn_tt99_template_data(self):
        return {
            'name': _('TT 99/2025/TT-BTC'),
            'parent': 'vn',
            'sequence': 0,
        }

    @template('vn_tt99', 'res.company')
    def _get_vn_tt99_res_company(self):
        return {
            self.env.company.id: {
                'accounting_regime': 'tt99',
            },
        }

    # Các hàm CSV dưới đây trỏ về dữ liệu của l10n_vn vì _parse_csv đọc theo module của template con.
    @template('vn_tt99', 'account.account')
    def _get_vn_tt99_account_account(self):
        data = self._parse_csv('vn', 'account.account', module='l10n_vn')
        # 133 và 333 là tài khoản tổng hợp thuế, không phải công nợ theo đối tượng.
        for xmlid, account_type in (
            ('chart133', 'asset_current'),
            ('chart333', 'liability_current'),
            ('chart3331', 'liability_current'),
            ('chart33312', 'liability_current'),
        ):
            data[xmlid].update({'account_type': account_type, 'reconcile': False})
        return data

    @template('vn_tt99', 'account.tax.group')
    def _get_vn_tt99_account_tax_group(self):
        return self._parse_csv('vn', 'account.tax.group', module='l10n_vn')

    @template('vn_tt99', 'account.tax')
    def _get_vn_tt99_account_tax(self):
        tax_data = self._parse_csv('vn', 'account.tax', module='l10n_vn')
        self._deref_account_tags('vn_tt99', tax_data)
        return tax_data
