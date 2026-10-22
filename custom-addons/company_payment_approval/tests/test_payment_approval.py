from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestPaymentApproval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.payment_approval_enabled = True
        cls.company.payment_approval_limit = 1000.0
        cls.partner = cls.env['res.partner'].create({
            'name': 'Payment Approval Vendor',
            'supplier_rank': 1,
        })
        cls.journal = cls.env['account.journal'].search([
            ('type', 'in', ('bank', 'cash')),
            ('company_id', '=', cls.company.id),
        ], limit=1)
        if not cls.journal:
            cls.journal = cls.env['account.journal'].create({
                'name': 'Payment Approval Bank',
                'type': 'bank',
                'code': 'PAPR',
                'company_id': cls.company.id,
            })
        group = cls.env.ref(
            'company_payment_approval.group_payment_approval_manager')
        group.write({'user_ids': [(4, cls.env.user.id)]})

    def _make_payment(self, amount=2000.0, payment_type='outbound'):
        return self.env['account.payment'].create({
            'payment_type': payment_type,
            'partner_type': 'supplier' if payment_type == 'outbound' else 'customer',
            'partner_id': self.partner.id,
            'amount': amount,
            'journal_id': self.journal.id,
        })

    def test_outbound_above_limit_requires_approval(self):
        payment = self._make_payment(amount=2000.0)
        self.assertTrue(payment.needs_payment_approval)
        self.assertEqual(payment.payment_approval_state, 'not_required')
        with self.assertRaises(UserError):
            payment.action_post()
        payment.action_request_payment_approval()
        self.assertEqual(payment.payment_approval_state, 'to_approve')
        payment.action_approve_payment()
        self.assertEqual(payment.payment_approval_state, 'approved')
        self.assertEqual(payment.payment_approver_id, self.env.user)
        payment.action_post()
        self.assertEqual(payment.state, 'paid')

    def test_outbound_below_limit_posts_directly(self):
        payment = self._make_payment(amount=500.0)
        self.assertFalse(payment.needs_payment_approval)
        payment.action_post()
        self.assertEqual(payment.state, 'paid')

    def test_inbound_above_limit_does_not_require_approval(self):
        payment = self._make_payment(amount=2000.0, payment_type='inbound')
        self.assertFalse(payment.needs_payment_approval)
        payment.action_post()
        self.assertEqual(payment.state, 'paid')

    def test_edit_amount_resets_approval(self):
        payment = self._make_payment(amount=2000.0)
        payment.action_request_payment_approval()
        payment.action_approve_payment()
        self.assertEqual(payment.payment_approval_state, 'approved')
        payment.write({'amount': 3000.0})
        self.assertEqual(payment.payment_approval_state, 'to_approve')
        self.assertFalse(payment.payment_approver_id)

    def test_refused_payment_cannot_post(self):
        payment = self._make_payment(amount=2000.0)
        payment.action_request_payment_approval()
        payment.action_refuse_payment()
        self.assertEqual(payment.payment_approval_state, 'refused')
        with self.assertRaises(UserError):
            payment.action_post()
