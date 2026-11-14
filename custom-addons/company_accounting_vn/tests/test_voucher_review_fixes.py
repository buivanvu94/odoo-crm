"""Mẫu in: thứ tự chữ ký 02-TT, Giám đốc ở 02-VT, TK Nợ/Có phiếu kho, thành tiền theo đơn vị tính."""
from odoo import Command
from odoo.tests import tagged

from .vn_accounting_test_base import VNAccountingCommon


@tagged('post_install', '-at_install')
class TestVoucherReviewFixes(VNAccountingCommon):

    def _render(self, xmlid, records):
        html, _kind = self.env['ir.actions.report']._render_qweb_html(xmlid, records.ids)
        return html.decode() if isinstance(html, bytes) else html

    def _payment(self, payment_type):
        return self.env['account.payment'].create({
            'payment_type': payment_type, 'partner_type': 'customer' if payment_type == 'inbound' else 'supplier',
            'partner_id': self.partner.id, 'amount': 1000000.0, 'journal_id': self.cash_journal.id})

    def _picking(self, picking_type_attr, uom=None, qty=10):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company.id)], limit=1)
        picking_type = warehouse[picking_type_attr]
        if not hasattr(self, 'product'):
            self.product = self.env['product.product'].create({
                'name': 'Hàng đóng thùng', 'is_storable': True, 'standard_price': 100.0, 'default_code': 'TH01'})
        move_vals = {
            'product_id': self.product.id, 'product_uom_qty': qty,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id}
        if uom:
            move_vals['uom_id'] = uom.id
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id, 'partner_id': self.partner.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'move_ids': [Command.create(move_vals)]})
        picking.action_confirm()
        picking.move_ids.quantity = qty
        return picking

    def test_payment_voucher_signature_order(self):
        payment_html = self._render('company_accounting_vn.action_report_payment_voucher', self._payment('outbound'))
        self.assertLess(payment_html.index('Thủ quỹ'), payment_html.index('Người lập phiếu'))
        self.assertLess(payment_html.index('Người lập phiếu'), payment_html.index('Người nhận tiền'))
        receipt_html = self._render('company_accounting_vn.action_report_payment_receipt', self._payment('inbound'))
        self.assertLess(receipt_html.index('Người nộp tiền'), receipt_html.index('Người lập phiếu'))
        self.assertLess(receipt_html.index('Người lập phiếu'), receipt_html.index('Thủ quỹ'))

    def test_issue_voucher_has_director_signature(self):
        picking = self._picking('in_type_id')
        self.assertIn('Giám đốc', self._render('company_accounting_vn.action_report_stock_issue', picking))
        self.assertNotIn('Giám đốc', self._render('company_accounting_vn.action_report_stock_receipt', picking))

    def test_stock_voucher_accounts_from_linked_entry(self):
        picking = self._picking('in_type_id')
        html = self._render('company_accounting_vn.action_report_stock_receipt', picking)
        self.assertIn('Chưa có bút toán kho liên kết', html)  # chưa có bút toán: để trống có chú thích
        entry = self.create_entry([('156', 1000, 0), ('331', 0, 1000, self.partner)])
        picking.move_ids.account_move_id = entry
        data = picking._get_vt_voucher_data()
        self.assertEqual((data['debit_codes'], data['credit_codes']), ('156', '331'))
        html = self._render('company_accounting_vn.action_report_stock_receipt', picking)
        self.assertIn('Nợ TK: <span>156</span>', html)
        self.assertNotIn('Chưa có bút toán kho liên kết', html)

    def test_amount_converts_uom_of_the_stock_line(self):
        box = self.env['uom.uom'].create({
            'name': 'Thùng 12 cái', 'relative_uom_id': self.env.ref('uom.product_uom_unit').id, 'relative_factor': 12})
        picking = self._picking('in_type_id', uom=box, qty=3)
        data = picking._get_vt_voucher_data()
        self.assertEqual(data['rows'][0]['uom'], 'Thùng 12 cái')
        self.assertEqual(data['rows'][0]['price'], 1200.0)  # 100 / cái x 12 cái / thùng
        self.assertEqual(data['total'], 3 * 12 * 100.0)

    def test_issue_voucher_prefers_posted_valuation(self):
        receipt = self._picking('in_type_id', qty=10)
        receipt.button_validate()
        self.product.standard_price = 200.0
        issue = self._picking('out_type_id', qty=4)
        issue.button_validate()
        self.assertEqual(issue.state, 'done')
        # Giá trị đã hạch toán của dòng xuất kho được ưu tiên hơn đơn giá / giá vốn chuẩn.
        move = issue.move_ids
        self.assertTrue(move.value)
        move.price_unit = 999.0
        data = issue._get_vt_voucher_data()
        self.assertEqual(data['total'], abs(move.value))
        self.assertNotEqual(data['total'], 4 * 999.0)
        self.assertEqual(data['rows'][0]['price'], abs(move.value) / 4)

    def test_transfer_voucher_does_not_print_cash_on_both_sides(self):
        # Chuyển tiền nội bộ: vế đối ứng là TK chuyển tiền của công ty, cấu hình cũng là TK trung gian của payment.
        transfer = self.company.transfer_account_id
        (self.cash_journal.inbound_payment_method_line_ids | self.cash_journal.outbound_payment_method_line_ids
         ).payment_account_id = transfer
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound', 'partner_type': 'supplier', 'amount': 100000.0,
            'journal_id': self.cash_journal.id, 'destination_account_id': transfer.id})
        payment.action_post()
        self.assertEqual(payment.outstanding_account_id, transfer)
        data = payment._get_voucher_data()
        self.assertEqual(data['credit_codes'], '111')
        self.assertEqual(data['debit_codes'], transfer.with_company(self.company).vn_display_code)
        receipt = self.env['account.payment'].create({
            'payment_type': 'inbound', 'partner_type': 'customer', 'amount': 100000.0,
            'journal_id': self.cash_journal.id, 'destination_account_id': transfer.id})
        receipt.action_post()
        data = receipt._get_voucher_data()
        self.assertEqual(data['debit_codes'], '111')
        self.assertEqual(data['credit_codes'], transfer.with_company(self.company).vn_display_code)
