"""Wizard lọc kỳ cho bộ báo cáo tài chính: xem màn hình, in PDF, xuất Excel."""
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..reports.financial_report_xlsx import build_xlsx


class VnFinancialReportWizard(models.TransientModel):
    _name = 'vn.financial.report.wizard'
    _description = 'Financial statements wizard'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    report_type = fields.Selection([
        ('all', 'Full set (B01, B02, B03)'),
        ('b01', 'B01-DN Statement of financial position'),
        ('b02', 'B02-DN Income statement'),
        ('b03', 'B03-DN Cash flow statement'),
    ], required=True, default='all')
    cash_flow_method = fields.Selection(
        [('direct', 'Direct method'), ('indirect', 'Indirect method')], required=True, default='direct')
    period_type = fields.Selection([
        ('month', 'Month'), ('quarter', 'Quarter'), ('year', 'Year'), ('custom', 'Custom dates')],
        required=True, default='month')
    year = fields.Integer(default=lambda self: fields.Date.context_today(self).year)
    month = fields.Selection([(str(m), str(m)) for m in range(1, 13)],
                             default=lambda self: str(fields.Date.context_today(self).month))
    quarter = fields.Selection([(str(q), 'Q%d' % q) for q in range(1, 5)], default='1')
    date_from = fields.Date(compute='_compute_dates', store=True, readonly=False)
    date_to = fields.Date(compute='_compute_dates', store=True, readonly=False)
    compare_previous = fields.Boolean(string='Compare with previous period')

    @api.depends('period_type', 'year', 'month', 'quarter')
    def _compute_dates(self):
        for wizard in self:
            year = wizard.year or fields.Date.context_today(wizard).year
            if wizard.period_type == 'month':
                start = date(year, int(wizard.month or 1), 1)
                end = start + relativedelta(months=1, days=-1)
            elif wizard.period_type == 'quarter':
                start = date(year, (int(wizard.quarter or 1) - 1) * 3 + 1, 1)
                end = start + relativedelta(months=3, days=-1)
            elif wizard.period_type == 'year':
                start, end = date(year, 1, 1), date(year, 12, 31)
            else:  # custom: giữ nguyên ngày người dùng nhập
                start = wizard.date_from or date(year, 1, 1)
                end = wizard.date_to or date(year, 12, 31)
            wizard.date_from, wizard.date_to = start, end

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if not wizard.date_from or not wizard.date_to or wizard.date_from > wizard.date_to:
                raise ValidationError(self.env._('Both dates are required and the start date must not be after the end date.'))

    def _previous_range(self):
        """Kỳ liền trước: lùi đúng một tháng/quý/năm; kỳ tùy chọn lùi đúng số ngày của kỳ hiện tại."""
        self.ensure_one()
        step = {'month': relativedelta(months=1), 'quarter': relativedelta(months=3),
                'year': relativedelta(years=1)}.get(self.period_type)
        if step:
            start = self.date_from - step
            return start, start + step - relativedelta(days=1)
        days = (self.date_to - self.date_from).days + 1
        return self.date_from - relativedelta(days=days), self.date_from - relativedelta(days=1)

    def _get_sections(self):
        """Danh sách báo cáo đã tính (kết quả ``vn.financial.report.build``) theo lựa chọn của wizard."""
        self.ensure_one()
        cash_flow = 'b03d' if self.cash_flow_method == 'direct' else 'b03i'
        types = {'all': ['b01', 'b02', cash_flow], 'b03': [cash_flow]}.get(self.report_type, [self.report_type])
        compare = self._previous_range() if self.compare_previous else None
        return self.env['vn.financial.report'].build_all(types, self.company_id, self.date_from, self.date_to, compare)

    def action_view(self):
        return self.env.ref('company_accounting_vn.action_report_vn_financial_html').report_action(self)

    def action_print_pdf(self):
        return self.env.ref('company_accounting_vn.action_report_vn_financial').report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        content = build_xlsx(self._get_sections(), self.company_id.name)
        attachment = self.env['ir.attachment'].create({
            'name': 'bao_cao_tai_chinh_%s_%s.xlsx' % (self.date_from, self.date_to),
            'raw': content,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/%d?download=true' % attachment.id, 'target': 'self'}
