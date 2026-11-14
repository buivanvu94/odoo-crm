from odoo.exceptions import UserError
from odoo.tests import tagged

from .vn_accounting_test_base import VNAccountingCommon


@tagged('post_install', '-at_install')
class TestVoucherReports(VNAccountingCommon):

    def _payment(self, payment_type, amount=15420000.0, **extra):
        return self.env['account.payment'].create({
            'payment_type': payment_type,
            'partner_type': 'customer' if payment_type == 'inbound' else 'supplier',
            'partner_id': self.partner.id,
            'amount': amount,
            'journal_id': self.cash_journal.id,
            'memo': 'Thu tiền hàng',
            **extra,
        })

    def _render(self, xmlid, records):
        html, _kind = self.env['ir.actions.report']._render_qweb_html(xmlid, records.ids)
        html = html.decode() if isinstance(html, bytes) else html
        return html

    def test_receiver_payer_defaults_from_partner(self):
        payment = self._payment('inbound')
        self.assertEqual(payment.receiver_payer_name, self.partner.name)
        self.assertIn('Lê Lợi', payment.receiver_payer_address)

    def test_receipt_voucher(self):
        payment = self._payment('inbound', attached_documents='03 hóa đơn')
        payment.action_post()
        data = payment._get_voucher_data()
        # The stored entry debits the outstanding account, the voucher shows the journal's cash account.
        raw_debit = payment.move_id.line_ids.filtered(lambda line: line.debit > 0).account_id
        self.assertEqual(raw_debit, payment.outstanding_account_id)
        self.assertNotEqual(raw_debit, self.cash_journal.default_account_id)
        self.assertEqual(data['amount'], 15420000.0)
        # The clearing account is shown as the journal's own cash account.
        self.assertEqual(data['debit_codes'], self.cash_journal.default_account_id.vn_display_code)
        self.assertEqual(data['credit_codes'], payment.destination_account_id.vn_display_code)
        html = self._render('company_accounting_vn.action_report_payment_receipt', payment)
        self.assertIn('PHIẾU THU', html)
        self.assertIn('Mười lăm triệu bốn trăm hai mươi nghìn đồng chẵn', html)
        self.assertIn('03 hóa đơn', html)

    def test_payment_voucher_draft(self):
        payment = self._payment('outbound')
        html = self._render('company_accounting_vn.action_report_payment_voucher', payment)
        self.assertIn('PHIẾU CHI', html)
        self.assertIn('Người nhận tiền', html)
        data = payment._get_voucher_data()
        self.assertEqual(data['credit_codes'], self.cash_journal.default_account_id.vn_display_code)

    def test_payment_approval_still_enforced(self):
        self.company.payment_approval_enabled = True
        payment = self._payment('outbound', amount=10000000.0)
        with self.assertRaises(UserError):
            payment.action_post()
        payment.payment_approval_state = 'approved'
        payment.action_post()
        self.assertEqual(payment.state, 'paid')

    def test_stock_vouchers(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company.id)], limit=1)
        product = self.env['product.product'].create({
            'name': 'Vật tư Test', 'is_storable': True, 'standard_price': 100.0,
            'default_code': 'VT01'})
        picking = self.env['stock.picking'].create({
            'picking_type_id': warehouse.in_type_id.id,
            'partner_id': self.partner.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': warehouse.lot_stock_id.id,
            'move_ids': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 10,
                'location_id': self.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': warehouse.lot_stock_id.id,
            })],
        })
        picking.action_confirm()
        picking.move_ids.quantity = 10
        data = picking._get_vt_voucher_data()
        self.assertEqual(data['total'], 1000.0)
        self.assertEqual(data['total_words'], 'Một nghìn đồng chẵn')
        html = self._render('company_accounting_vn.action_report_stock_receipt', picking)
        self.assertIn('PHIẾU NHẬP KHO', html)
        self.assertIn('VT01', html)
        html = self._render('company_accounting_vn.action_report_stock_issue', picking)
        self.assertIn('PHIẾU XUẤT KHO', html)
        self.assertIn('Một nghìn đồng chẵn', html)
