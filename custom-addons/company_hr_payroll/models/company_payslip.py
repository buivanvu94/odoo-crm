from datetime import date, datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

MONTHS = [(str(i), 'Tháng %s' % i) for i in range(1, 13)]


class CompanyPayslip(models.Model):
    _name = 'company.payslip'
    _description = 'Phiếu lương'
    _order = 'year desc, month desc, employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã phiếu', default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    department_id = fields.Many2one(
        'hr.department', related='employee_id.department_id', store=True, string='Phòng ban')
    company_id = fields.Many2one(
        'res.company', related='employee_id.company_id', store=True, string='Công ty')
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string='Tiền tệ')
    month = fields.Selection(MONTHS, string='Tháng', required=True,
                             default=lambda self: str(fields.Date.today().month))
    year = fields.Integer(string='Năm', required=True,
                          default=lambda self: fields.Date.today().year)
    date_from = fields.Date(string='Từ ngày', compute='_compute_period', store=True)
    date_to = fields.Date(string='Đến ngày', compute='_compute_period', store=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Nháp'),
            ('confirmed', 'Đã xác nhận'),
            ('paid', 'Đã trả'),
        ],
        string='Trạng thái', default='draft', tracking=True,
    )

    worked_days = fields.Integer(string='Ngày công', readonly=True)
    worked_hours = fields.Float(string='Giờ làm việc', readonly=True)
    overtime_hours = fields.Float(string='Giờ làm thêm', readonly=True)
    standard_days = fields.Integer(string='Ngày công chuẩn', readonly=True)

    contract_wage = fields.Monetary(
        string='Lương hợp đồng', currency_field='currency_id', readonly=True)
    basic_salary = fields.Monetary(
        string='Lương theo ngày công', currency_field='currency_id', readonly=True)
    overtime_amount = fields.Monetary(
        string='Tiền làm thêm', currency_field='currency_id', readonly=True)
    allowance_amount = fields.Monetary(
        string='Phụ cấp', currency_field='currency_id', readonly=True)
    gross_salary = fields.Monetary(
        string='Tổng thu nhập', currency_field='currency_id', readonly=True)

    insurance_base = fields.Monetary(
        string='Lương đóng bảo hiểm', currency_field='currency_id', readonly=True)
    insurance_employee = fields.Monetary(
        string='Bảo hiểm NLĐ đóng', currency_field='currency_id', readonly=True)
    insurance_employer = fields.Monetary(
        string='Bảo hiểm NSDLĐ đóng', currency_field='currency_id', readonly=True)

    personal_deduction = fields.Monetary(
        string='Giảm trừ bản thân', currency_field='currency_id', readonly=True)
    dependent_deduction = fields.Monetary(
        string='Giảm trừ người phụ thuộc', currency_field='currency_id', readonly=True)
    taxable_income = fields.Monetary(
        string='Thu nhập tính thuế', currency_field='currency_id', readonly=True)
    pit_amount = fields.Monetary(
        string='Thuế TNCN', currency_field='currency_id', readonly=True)
    net_salary = fields.Monetary(
        string='Thực lĩnh', currency_field='currency_id', readonly=True)

    payment_date = fields.Date(string='Ngày trả lương', readonly=True)
    note = fields.Text(string='Ghi chú')

    @api.depends('month', 'year')
    def _compute_period(self):
        for slip in self:
            month = int(slip.month or 1)
            year = slip.year or fields.Date.today().year
            slip.date_from = date(year, month, 1)
            if month == 12:
                next_month = date(year + 1, 1, 1)
            else:
                next_month = date(year, month + 1, 1)
            slip.date_to = next_month - timedelta(days=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('company.payslip') or '/'
        return super().create(vals_list)

    @api.model
    def _bracket_pit(self, taxable):
        brackets = (
            (5000000.0, 0.05, 0.0),
            (10000000.0, 0.10, 250000.0),
            (18000000.0, 0.15, 750000.0),
            (32000000.0, 0.20, 1650000.0),
            (52000000.0, 0.25, 3250000.0),
            (80000000.0, 0.30, 5850000.0),
            (float('inf'), 0.35, 9850000.0),
        )
        for limit, rate, deduction in brackets:
            if taxable <= limit:
                return max(0.0, taxable * rate - deduction)
        return 0.0

    def _prepare_salary_vals(self):
        self.ensure_one()
        employee = self.employee_id
        company = self.company_id or self.env.company
        start = datetime.combine(self.date_from, time.min)
        end = datetime.combine(self.date_to, time.max)
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start),
            ('check_in', '<=', end),
        ])
        worked_hours = sum(attendances.mapped('worked_hours'))
        worked_days = len({att.check_in.date() for att in attendances if att.check_in})
        standard_days = company.payroll_standard_days or 26
        contract_wage = employee.monthly_wage or 0.0
        allowance = employee.payroll_allowance or 0.0

        paid_days = min(worked_days, standard_days)
        basic_salary = contract_wage * paid_days / standard_days if standard_days else 0.0
        standard_hours = standard_days * 8.0
        overtime_hours = max(0.0, worked_hours - standard_hours)
        hourly_rate = contract_wage / standard_hours if standard_hours else 0.0
        overtime_amount = hourly_rate * (company.payroll_overtime_rate or 1.5) * overtime_hours
        gross_salary = basic_salary + overtime_amount + allowance

        insurance_base = min(
            employee.insurance_salary or contract_wage,
            company.payroll_insurance_cap or float('inf'),
        )
        employee_rate = (company.payroll_employee_insurance_rate or 10.5) / 100.0
        employer_rate = (company.payroll_employer_insurance_rate or 21.5) / 100.0
        insurance_employee = insurance_base * employee_rate
        insurance_employer = insurance_base * employer_rate

        personal_deduction = company.payroll_personal_deduction or 11000000.0
        dependent_deduction = (employee.dependent_count or 0) * (
            company.payroll_dependent_deduction or 4400000.0)
        taxable_income = max(
            0.0, gross_salary - insurance_employee - personal_deduction - dependent_deduction)
        pit_amount = self._bracket_pit(taxable_income)
        net_salary = gross_salary - insurance_employee - pit_amount

        return {
            'standard_days': standard_days,
            'worked_days': worked_days,
            'worked_hours': worked_hours,
            'overtime_hours': overtime_hours,
            'contract_wage': contract_wage,
            'basic_salary': round(basic_salary, 2),
            'overtime_amount': round(overtime_amount, 2),
            'allowance_amount': round(allowance, 2),
            'gross_salary': round(gross_salary, 2),
            'insurance_base': round(insurance_base, 2),
            'insurance_employee': round(insurance_employee, 2),
            'insurance_employer': round(insurance_employer, 2),
            'personal_deduction': round(personal_deduction, 2),
            'dependent_deduction': round(dependent_deduction, 2),
            'taxable_income': round(taxable_income, 2),
            'pit_amount': round(pit_amount, 2),
            'net_salary': round(net_salary, 2),
        }

    def action_compute(self):
        for slip in self:
            if slip.state != 'draft':
                raise UserError(_('Chỉ tính lại phiếu lương ở trạng thái Nháp.'))
            slip.write(slip._prepare_salary_vals())

    def action_confirm(self):
        for slip in self:
            if slip.state != 'draft':
                continue
            if not slip.worked_hours:
                slip.write(slip._prepare_salary_vals())
            slip.state = 'confirmed'

    def action_pay(self):
        for slip in self:
            if slip.state != 'confirmed':
                raise UserError(_('Chỉ xác nhận thanh toán phiếu lương đã xác nhận.'))
            slip.write({'state': 'paid', 'payment_date': fields.Date.today()})

    def action_reset(self):
        self.write({'state': 'draft', 'payment_date': False})
