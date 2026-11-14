from odoo import models

from ..tools.vietnamese_converter import amount_to_words_vi, format_date_vi


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_vt_move_values(self, move):
        """``(đơn giá theo đơn vị của dòng, thành tiền)`` của một dòng kho.

        Giá và số lượng được quy đổi qua đơn vị tính của sản phẩm nên đơn vị của dòng (thùng, hộp...) khác
        đơn vị sản phẩm vẫn ra đúng thành tiền. Ưu tiên giá trị đã hạch toán của dòng kho đã hoàn tất
        (stock_account); nếu chưa có thì dùng giá của dòng kho (nhập) hoặc giá vốn chuẩn của sản phẩm.
        """
        product = move.product_id
        qty_move_uom = move.quantity
        qty_product_uom = move.quantity_product_uom
        valued = abs(move.value) if move.state == 'done' and 'value' in move._fields else 0.0
        if valued:
            amount = valued
        else:
            # price_unit và standard_price đều tính theo đơn vị của sản phẩm.
            price_product_uom = abs(move.price_unit) or product.with_company(move.company_id).standard_price
            amount = qty_product_uom * price_product_uom
        price = amount / qty_move_uom if qty_move_uom else 0.0
        return price, amount

    def _get_vt_accounts(self):
        """``(mã TK Nợ, mã TK Có)`` từ bút toán kho liên kết (stock_account); rỗng nếu không có."""
        self.ensure_one()
        entries = self.move_ids.filtered(lambda m: m.state != 'cancel').mapped('account_move_id')
        lines = entries.with_company(self.company_id).line_ids.filtered(lambda line: line.display_type not in (
            'line_section', 'line_subsection', 'line_note'))
        debit = lines.filtered(lambda line: line.debit > 0).account_id
        credit = lines.filtered(lambda line: line.credit > 0).account_id
        return ', '.join(dict.fromkeys(debit.mapped('vn_display_code'))), ', '.join(
            dict.fromkeys(credit.mapped('vn_display_code')))

    def _get_vt_voucher_data(self):
        """Values for the 01-VT (goods receipt) and 02-VT (goods issue) QWeb templates."""
        self.ensure_one()
        self = self.with_company(self.company_id)  # account codes depend on the company of the picking
        company = self.company_id
        rows = []
        total = 0.0
        for move in self.move_ids.filtered(lambda m: m.state != 'cancel'):
            price, amount = self._get_vt_move_values(move)
            total += amount
            rows.append({
                'move': move,
                'name': move.product_id.display_name,
                'code': move.product_id.default_code or '',
                'uom': move.uom_id.name,
                'demand_qty': move.product_uom_qty,
                'done_qty': move.quantity,
                'price': price,
                'amount': amount,
            })
        currency = company.currency_id
        voucher_date = self.date_done or self.scheduled_date
        debit_codes, credit_codes = self._get_vt_accounts()
        return {
            'rows': rows,
            'total': total,
            'currency': currency,
            'total_words': amount_to_words_vi(total) if currency.name == 'VND' else '',
            'date_text': format_date_vi(voucher_date and voucher_date.date()),
            'debit_codes': debit_codes,
            'credit_codes': credit_codes,
        }
