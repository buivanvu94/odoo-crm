from odoo import api, fields, models

MONTHS = [(str(i), 'Tháng %s' % i) for i in range(1, 13)]


class CompanyKpi(models.Model):
    _name = 'company.kpi'
    _description = 'Chỉ số KPI nhân viên'
    _order = 'year desc, month desc, employee_id'

    name = fields.Char(string='Chỉ số', required=True)
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    department_id = fields.Many2one(
        'hr.department', related='employee_id.department_id', store=True, string='Phòng ban')
    company_id = fields.Many2one(
        'res.company', related='employee_id.company_id', store=True, string='Công ty')
    month = fields.Selection(MONTHS, string='Tháng', required=True,
                             default=lambda self: str(fields.Date.today().month))
    year = fields.Integer(string='Năm', required=True,
                          default=lambda self: fields.Date.today().year)
    unit = fields.Char(string='Đơn vị', default='%')
    target = fields.Float(string='Mục tiêu', required=True)
    actual = fields.Float(string='Thực tế')
    weight = fields.Float(string='Trọng số', default=1.0)
    achievement = fields.Float(
        string='Tỷ lệ đạt (%)', compute='_compute_achievement', store=True)
    score = fields.Float(
        string='Điểm', compute='_compute_achievement', store=True)
    passed = fields.Boolean(
        string='Đạt KPI', compute='_compute_achievement', store=True)
    note = fields.Text(string='Ghi chú')

    @api.depends('target', 'actual', 'weight')
    def _compute_achievement(self):
        for kpi in self:
            kpi.achievement = (kpi.actual / kpi.target * 100.0) if kpi.target else 0.0
            kpi.score = min(kpi.achievement, 150.0) * (kpi.weight or 1.0)
            kpi.passed = kpi.achievement >= 100.0
