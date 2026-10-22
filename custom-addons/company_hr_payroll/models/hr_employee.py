from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    payroll_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string='Payroll Currency')
    monthly_wage = fields.Monetary(
        string='Lương cơ bản / tháng',
        currency_field='payroll_currency_id',
        groups='company_hr_payroll.group_payroll_user',
    )
    payroll_allowance = fields.Monetary(
        string='Phụ cấp / tháng',
        currency_field='payroll_currency_id',
        groups='company_hr_payroll.group_payroll_user',
    )
    insurance_salary = fields.Monetary(
        string='Lương đóng bảo hiểm',
        currency_field='payroll_currency_id',
        groups='company_hr_payroll.group_payroll_user',
        help='Để trống sẽ dùng lương cơ bản.',
    )
    dependent_count = fields.Integer(
        string='Số người phụ thuộc',
        groups='company_hr_payroll.group_payroll_user',
    )
