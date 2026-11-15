from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.binary import BinaryBytes
from odoo.tools.date_utils import end_of, start_of

from odoo.addons.company_accounting_vn.reports.ledger_layout import REPORT_TYPES, TITLES
from odoo.addons.company_accounting_vn.reports.ledger_xlsx import build_xlsx

SCREEN_LIMIT_PARAM = 'company_accounting_vn.screen_row_limit'
DEFAULT_SCREEN_ROW_LIMIT = 2000
MIN_SCREEN_ROW_LIMIT = 3


class AccountingReportWizard(models.TransientModel):
    _name = 'accounting.report.wizard'
    _description = 'Vietnamese accounting books wizard'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    report_type = fields.Selection(REPORT_TYPES, required=True, default='ledger')
    date_from = fields.Date(required=True, default=lambda self: start_of(fields.Date.context_today(self), 'month'))
    date_to = fields.Date(required=True, default=lambda self: end_of(fields.Date.context_today(self), 'month'))
    account_ids = fields.Many2many(
        'account.account', 'vn_report_wizard_account_rel', 'wizard_id', 'account_id', string='Accounts',
        help='Journal, ledger and trial balance only. A parent account also selects its sub-accounts.')
    partner_ids = fields.Many2many(
        'res.partner', 'vn_report_wizard_partner_rel', 'wizard_id', 'partner_id', string='Partners')
    journal_ids = fields.Many2many(
        'account.journal', 'vn_report_wizard_journal_rel', 'wizard_id', 'journal_id', string='Journals')
    line_ids = fields.One2many('accounting.report.line', 'wizard_id')
    xlsx_file = fields.Binary(attachment=False, readonly=True)
    xlsx_filename = fields.Char(readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_('The start date must not be after the end date.'))

    # --- chọn nhanh kỳ: tháng / quý / năm chứa "đến ngày" ---------------------------------

    def _set_period(self, granularity):
        self.ensure_one()
        anchor = self.date_to or fields.Date.context_today(self)
        self.write({'date_from': start_of(anchor, granularity), 'date_to': end_of(anchor, granularity)})
        return {
            'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
            'view_mode': 'form', 'target': 'new',
        }

    def action_period_month(self):
        return self._set_period('month')

    def action_period_quarter(self):
        return self._set_period('quarter')

    def action_period_year(self):
        return self._set_period('year')

    # --- kết quả ---------------------------------------------------------------------------

    def _get_report_data(self):
        """Kiểm quyền rồi tính dữ liệu sổ; dùng chung cho màn hình, PDF và Excel."""
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_user'):
            raise AccessError(_('Only accountants can print accounting books.'))
        if self.company_id not in self.env.user.company_ids:
            raise AccessError(_('You are not allowed to access this company.'))
        # Mã tài khoản phụ thuộc công ty: tính trong ngữ cảnh công ty của wizard.
        return self.with_company(self.company_id).env['vn.ledger.engine'].build(self)

    def _screen_row_limit(self):
        """Số dòng tối đa tạo bản ghi tạm khi xem trên màn hình (tham số hệ thống, mặc định 2000).

        Tối thiểu 3: dòng thông báo, một dòng dữ liệu và dòng tổng cộng (giá trị nhỏ hơn làm cắt sai).
        """
        configured = self.env['ir.config_parameter'].sudo().get_int(SCREEN_LIMIT_PARAM, 0)
        return max(configured, MIN_SCREEN_ROW_LIMIT) if configured > 0 else DEFAULT_SCREEN_ROW_LIMIT

    def action_view_screen(self):
        data = self._get_report_data()
        rows, limit = data['rows'], self._screen_row_limit()
        if len(rows) > limit:
            # Giữ dòng tổng cộng cuối sổ; phần còn lại xem bằng PDF / Excel (không giới hạn).
            notice = {'kind': 'group', 'label': _(
                'Showing only the first %(shown)s of %(total)s lines. Narrow the filters, or print the PDF / '
                'export Excel to see everything.', shown=limit - 2, total=len(rows) - 1)}
            rows = [notice] + rows[:limit - 2] + rows[-1:]
        self.line_ids.unlink()
        self.env['accounting.report.line'].create([
            dict(row, wizard_id=self.id, sequence=seq) for seq, row in enumerate(rows)])
        is_trial = self.report_type == 'trial'
        view = self.env.ref('company_accounting_vn.view_accounting_report_line_%s' % ('trial' if is_trial else 'list'))
        return {
            'type': 'ir.actions.act_window', 'name': TITLES[self.report_type],
            'res_model': 'accounting.report.line', 'views': [(view.id, 'list')],
            'domain': [('wizard_id', '=', self.id)], 'target': 'current',
        }

    def action_print_pdf(self):
        self._get_report_data()  # kiểm quyền/ngày sớm, trước khi sinh PDF
        return self.env.ref('company_accounting_vn.action_report_vn_ledger').report_action(self)

    def action_export_xlsx(self):
        data = self._get_report_data()
        self.write({
            'xlsx_file': BinaryBytes(build_xlsx(data, self.company_id.name)),
            'xlsx_filename': '%s_%s_%s.xlsx' % (self.report_type, self.date_from, self.date_to),
        })
        return {
            'type': 'ir.actions.act_url', 'target': 'self',
            'url': '/web/content/%s/%s/xlsx_file/%s?download=true' % (self._name, self.id, self.xlsx_filename),
        }
