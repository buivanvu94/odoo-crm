from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSaleApproval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.sale_max_discount = 10.0
        cls.company.sale_check_below_cost = True
        cls.partner = cls.env['res.partner'].create({'name': 'Approval Customer'})
        cls.product = cls.env['product.product'].create({
            'name': 'Approval Product',
            'list_price': 100.0,
            'standard_price': 80.0,
            'type': 'consu',
        })
        cls.admin = cls.env.ref('base.user_admin')

    def _make_order(self, price=100.0, discount=0.0):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': price,
                'discount': discount,
            })],
        })

    def test_discount_requires_approval(self):
        order = self._make_order(discount=50.0)
        self.assertTrue(order.needs_price_approval)
        self.assertEqual(order.max_line_discount, 50.0)
        with self.assertRaises(UserError):
            order.action_confirm()
        order.action_request_price_approval()
        self.assertEqual(order.price_approval_state, 'to_approve')
        order.with_user(self.admin).action_approve_price()
        self.assertEqual(order.price_approval_state, 'approved')
        order.action_confirm()
        self.assertEqual(order.state, 'sale')

    def test_below_cost_requires_approval(self):
        order = self._make_order(price=50.0, discount=0.0)
        self.assertTrue(order.has_below_cost)
        self.assertTrue(order.needs_price_approval)
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_normal_order_needs_no_approval(self):
        order = self._make_order(price=100.0, discount=5.0)
        self.assertFalse(order.needs_price_approval)
        order.action_confirm()
        self.assertEqual(order.state, 'sale')

    def test_edit_after_approval_resets_state(self):
        order = self._make_order(discount=50.0)
        order.action_request_price_approval()
        order.with_user(self.admin).action_approve_price()
        order.write({'order_line': [(0, 0, {
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 90.0,
            'discount': 20.0,
        })]})
        self.assertEqual(order.price_approval_state, 'to_approve')
