from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase


class TestPayroll(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.payroll_standard_days = 26
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Payroll Test Employee',
            'monthly_wage': 26000000.0,
            'payroll_allowance': 1000000.0,
            'dependent_count': 1,
        })
        start = datetime(2026, 3, 2, 8, 0)
        for day in range(20):
            check_in = start + timedelta(days=day)
            cls.env['hr.attendance'].create({
                'employee_id': cls.employee.id,
                'check_in': check_in,
                'check_out': check_in + timedelta(hours=8),
            })

    def _make_payslip(self):
        return self.env['company.payslip'].create({
            'employee_id': self.employee.id,
            'month': '3',
            'year': 2026,
        })

    def test_payslip_from_attendance(self):
        slip = self._make_payslip()
        self.assertTrue(slip.name.startswith('PS/2026/'))
        slip.action_compute()
        self.assertEqual(slip.worked_days, 20)
        self.assertEqual(slip.worked_hours, 160.0)
        self.assertEqual(slip.basic_salary, 20000000.0)
        self.assertEqual(slip.gross_salary, 21000000.0)
        self.assertEqual(slip.insurance_base, 26000000.0)
        self.assertAlmostEqual(slip.insurance_employee, 2730000.0, places=2)
        self.assertAlmostEqual(slip.taxable_income, 2870000.0, places=2)
        self.assertAlmostEqual(slip.pit_amount, 143500.0, places=2)
        self.assertAlmostEqual(slip.net_salary, 18126500.0, places=2)

    def test_state_flow(self):
        slip = self._make_payslip()
        slip.action_compute()
        slip.action_confirm()
        self.assertEqual(slip.state, 'confirmed')
        slip.action_pay()
        self.assertEqual(slip.state, 'paid')
        self.assertTrue(slip.payment_date)

    def test_pit_brackets(self):
        payslip = self.env['company.payslip']
        self.assertAlmostEqual(payslip._bracket_pit(5000000.0), 250000.0)
        self.assertAlmostEqual(payslip._bracket_pit(10000000.0), 750000.0)
        self.assertAlmostEqual(payslip._bracket_pit(0.0), 0.0)


class TestKpi(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({'name': 'KPI Test Employee'})

    def test_kpi_score(self):
        kpi = self.env['company.kpi'].create({
            'name': 'Doanh số',
            'employee_id': self.employee.id,
            'month': '3',
            'year': 2026,
            'target': 100.0,
            'actual': 120.0,
        })
        self.assertAlmostEqual(kpi.achievement, 120.0)
        self.assertTrue(kpi.passed)
        self.assertAlmostEqual(kpi.score, 120.0)

        kpi.actual = 80.0
        self.assertAlmostEqual(kpi.achievement, 80.0)
        self.assertFalse(kpi.passed)
