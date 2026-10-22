{
    'name': 'Company HR Payroll & KPI',
    'version': '20.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Tính lương từ chấm công, bảo hiểm, thuế TNCN và KPI',
    'description': """
Company HR Payroll & KPI
========================

Odoo Community không có module hr_payroll, module này bổ sung:

* Lương cơ bản, phụ cấp, số người phụ thuộc trên hồ sơ nhân viên.
* Phiếu lương tính từ dữ liệu chấm công (hr.attendance).
* Bảo hiểm bắt buộc: BHXH 8%, BHYT 1.5%, BHTN 1% (người lao động)
  và 21.5% (người sử dụng lao động).
* Thuế thu nhập cá nhân theo biểu lũy tiến 7 bậc.
* KPI theo nhân viên / tháng / năm.
    """,
    'author': 'My Company',
    'license': 'LGPL-3',
    'depends': ['hr_attendance'],
    'data': [
        'security/company_hr_payroll_security.xml',
        'security/ir.access.csv',
        'data/ir_sequence_data.xml',
        'views/res_company_views.xml',
        'views/hr_employee_views.xml',
        'views/company_payslip_views.xml',
        'views/company_kpi_views.xml',
        'views/company_hr_payroll_menus.xml',
    ],
    'installable': True,
}
