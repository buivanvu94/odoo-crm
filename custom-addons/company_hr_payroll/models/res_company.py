from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    payroll_standard_days = fields.Integer(
        string='Ngày công chuẩn / tháng', default=26)
    payroll_personal_deduction = fields.Monetary(
        string='Giảm trừ gia cảnh bản thân',
        currency_field='currency_id',
        default=11000000.0,
    )
    payroll_dependent_deduction = fields.Monetary(
        string='Giảm trừ mỗi người phụ thuộc',
        currency_field='currency_id',
        default=4400000.0,
    )
    payroll_insurance_cap = fields.Monetary(
        string='Mức lương đóng bảo hiểm tối đa',
        currency_field='currency_id',
        default=46800000.0,
    )
    payroll_overtime_rate = fields.Float(
        string='Hệ số làm thêm giờ', default=1.5)
    payroll_employee_insurance_rate = fields.Float(
        string='Tỷ lệ BH người lao động (%)', default=10.5)
    payroll_employer_insurance_rate = fields.Float(
        string='Tỷ lệ BH người sử dụng lao động (%)', default=21.5)
