from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestLogistics(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.internal_transfer_approval = True
        cls.company.internal_transfer_limit = 1000.0
        cls.product = cls.env['product.product'].create({
            'name': 'Transfer Product',
            'type': 'consu',
            'standard_price': 100.0,
        })
        cls.picking_type = cls.env.ref('stock.picking_type_internal')
        cls.location = cls.env.ref('stock.stock_location_stock')
        cls.location_dest = cls.env.ref('stock.stock_location_company')

    def _make_picking(self, quantity=20.0):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type.id,
            'location_id': self.location.id,
            'location_dest_id': self.location_dest.id,
        })
        self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom_qty': quantity,
            'uom_id': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location.id,
            'location_dest_id': self.location_dest.id,
        })
        return picking

    def test_internal_transfer_requires_approval(self):
        picking = self._make_picking()
        self.assertEqual(picking.internal_transfer_value, 2000.0)
        self.assertTrue(picking.logistics_needs_approval)
        with self.assertRaises(UserError):
            picking.button_validate()
        picking.action_request_logistics_approval()
        self.assertEqual(picking.logistics_approval_state, 'to_approve')
        picking.with_user(self.env.ref('base.user_admin')).action_approve_logistics()
        self.assertEqual(picking.logistics_approval_state, 'approved')

    def test_small_transfer_needs_no_approval(self):
        picking = self._make_picking(quantity=5.0)
        self.assertFalse(picking.logistics_needs_approval)
        self.assertEqual(picking.internal_transfer_value, 500.0)

    def test_extract_tracking_ref(self):
        picking = self.env['stock.picking']
        self.assertEqual(
            picking._extract_tracking_ref('{"data": {"order_code": "GHN123"}}'),
            'GHN123',
        )
        self.assertFalse(picking._extract_tracking_ref('not json'))

