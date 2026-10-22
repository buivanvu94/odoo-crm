from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestCompanyApprovalRequest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = new_test_user(
            cls.env, login='approval_employee',
            groups='base.group_user,company_approval.group_approval_user',
        )
        cls.manager = new_test_user(
            cls.env, login='approval_manager',
            groups='base.group_user,company_approval.group_approval_manager',
        )

    def _create_request(self, user=None, **values):
        values.setdefault('reason', 'Need a new laptop for the design team.')
        return self.env['company.approval.request'].with_user(user or self.employee).create(values)

    def test_reference_is_generated(self):
        request = self._create_request()
        self.assertNotEqual(request.name, '/')
        self.assertEqual(request.state, 'draft')
        self.assertEqual(request.requested_by, self.employee)

    def test_full_approval_flow(self):
        request = self._create_request(amount=1500.0)
        request.action_submit()
        self.assertEqual(request.state, 'submitted')

        request.with_user(self.manager).action_approve()
        self.assertEqual(request.state, 'approved')
        self.assertEqual(request.approver_id, self.manager)
        self.assertTrue(request.date_approval)

    def test_refuse_flow(self):
        request = self._create_request()
        request.action_submit()
        request.with_user(self.manager).action_refuse()
        self.assertEqual(request.state, 'refused')
        self.assertEqual(request.approver_id, self.manager)

    def test_employee_cannot_approve(self):
        request = self._create_request()
        request.action_submit()
        with self.assertRaises(AccessError):
            request.with_user(self.employee).action_approve()

    def test_cannot_submit_twice(self):
        request = self._create_request()
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_submit()

    def test_employee_cannot_read_other_requests(self):
        other_request = self._create_request(user=self.manager)
        with self.assertRaises(AccessError):
            other_request.with_user(self.employee).read(['name'])
