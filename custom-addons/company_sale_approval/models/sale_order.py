from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    max_line_discount = fields.Float(
        string='Chiết khấu cao nhất (%)',
        compute='_compute_price_approval',
        store=True,
    )
    has_below_cost = fields.Boolean(
        string='Có dòng dưới giá vốn',
        compute='_compute_price_approval',
        store=True,
    )
    needs_price_approval = fields.Boolean(
        string='Cần duyệt giá',
        compute='_compute_price_approval',
        store=True,
    )
    price_approval_state = fields.Selection(
        selection=[
            ('not_required', 'Không cần duyệt'),
            ('to_approve', 'Chờ duyệt'),
            ('approved', 'Đã duyệt'),
            ('refused', 'Từ chối'),
        ],
        string='Trạng thái duyệt giá',
        default='not_required',
        copy=False,
        tracking=True,
    )
    price_approver_id = fields.Many2one(
        'res.users',
        string='Người duyệt giá',
        copy=False,
        readonly=True,
    )
    price_approval_date = fields.Datetime(
        string='Ngày duyệt giá',
        copy=False,
        readonly=True,
    )
    price_approval_note = fields.Text(
        string='Ghi chú duyệt giá',
        copy=False,
    )

    @api.depends(
        'order_line.discount',
        'order_line.price_unit',
        'order_line.product_id',
        'order_line.display_type',
        'company_id.sale_max_discount',
        'company_id.sale_check_below_cost',
    )
    def _compute_price_approval(self):
        for order in self:
            max_discount = 0.0
            below_cost = False
            for line in order.order_line:
                if line.display_type:
                    continue
                max_discount = max(max_discount, line.discount or 0.0)
                if order.company_id.sale_check_below_cost and line.product_id:
                    cost = line.product_id.with_company(order.company_id).standard_price
                    unit_price = (line.price_unit or 0.0) * (1 - (line.discount or 0.0) / 100.0)
                    if cost and unit_price < cost:
                        below_cost = True
            limit = order.company_id.sale_max_discount or 0.0
            order.max_line_discount = max_discount
            order.has_below_cost = below_cost
            order.needs_price_approval = bool(max_discount > limit or below_cost)

    def write(self, vals):
        res = super().write(vals)
        if 'order_line' in vals or 'partner_id' in vals:
            approved = self.filtered(lambda o: o.price_approval_state == 'approved')
            if approved:
                approved.write({'price_approval_state': 'to_approve'})
        return res

    def action_confirm(self):
        for order in self:
            if order.needs_price_approval and order.price_approval_state != 'approved':
                raise UserError(_(
                    'Đơn %(order)s cần duyệt giá trước khi xác nhận.\n'
                    'Chiết khấu cao nhất: %(discount).2f%% (giới hạn %(limit).2f%%).'
                ) % {
                    'order': order.name,
                    'discount': order.max_line_discount,
                    'limit': order.company_id.sale_max_discount or 0.0,
                })
        return super().action_confirm()

    def action_request_price_approval(self):
        for order in self:
            if not order.needs_price_approval:
                order.price_approval_state = 'not_required'
            else:
                order.write({'price_approval_state': 'to_approve'})

    def action_approve_price(self):
        if not self.env.user.has_group('company_sale_approval.group_sale_price_manager'):
            raise UserError(_('Chỉ quản lý kinh doanh mới được duyệt giá.'))
        for order in self:
            if not order.needs_price_approval:
                order.price_approval_state = 'not_required'
                continue
            order.write({
                'price_approval_state': 'approved',
                'price_approver_id': self.env.user.id,
                'price_approval_date': fields.Datetime.now(),
            })

    def action_refuse_price(self):
        if not self.env.user.has_group('company_sale_approval.group_sale_price_manager'):
            raise UserError(_('Chỉ quản lý kinh doanh mới được từ chối duyệt giá.'))
        for order in self:
            order.write({
                'price_approval_state': 'refused',
                'price_approver_id': self.env.user.id,
                'price_approval_date': fields.Datetime.now(),
            })

    def action_reset_price_approval(self):
        for order in self:
            order.write({
                'price_approval_state': 'not_required',
                'price_approver_id': False,
                'price_approval_date': False,
            })
