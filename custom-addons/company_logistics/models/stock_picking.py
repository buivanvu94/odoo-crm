import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    logistics_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string='Currency')
    internal_transfer_value = fields.Monetary(
        string='Giá trị chuyển kho',
        compute='_compute_logistics_approval',
        store=True,
        currency_field='logistics_currency_id',
    )
    logistics_needs_approval = fields.Boolean(
        string='Cần duyệt chuyển kho',
        compute='_compute_logistics_approval',
        store=True,
    )
    logistics_approval_state = fields.Selection(
        selection=[
            ('not_required', 'Không cần duyệt'),
            ('to_approve', 'Chờ duyệt'),
            ('approved', 'Đã duyệt'),
            ('refused', 'Từ chối'),
        ],
        string='Trạng thái duyệt kho',
        default='not_required',
        copy=False,
        tracking=True,
    )
    logistics_approver_id = fields.Many2one(
        'res.users', string='Người duyệt kho', copy=False, readonly=True)
    logistics_approval_date = fields.Datetime(
        string='Ngày duyệt kho', copy=False, readonly=True)
    shipment_log_ids = fields.One2many(
        'company.shipment.log', 'picking_id', string='Lịch sử vận đơn')

    @api.depends(
        'picking_type_id.code',
        'move_ids.product_id',
        'move_ids.product_uom_qty',
        'company_id.internal_transfer_approval',
        'company_id.internal_transfer_limit',
    )
    def _compute_logistics_approval(self):
        for picking in self:
            value = sum(
                (move.product_id.with_company(picking.company_id).standard_price or 0.0)
                * (move.product_uom_qty or 0.0)
                for move in picking.move_ids
            )
            picking.internal_transfer_value = value
            picking.logistics_needs_approval = bool(
                picking.picking_type_id.code == 'internal'
                and picking.company_id.internal_transfer_approval
                and value > (picking.company_id.internal_transfer_limit or 0.0)
            )

    def button_validate(self):
        for picking in self:
            if picking.logistics_needs_approval and picking.logistics_approval_state != 'approved':
                raise UserError(_(
                    'Phiếu %(name)s có giá trị %(value)s vượt hạn mức chuyển kho. '
                    'Cần quản lý kho duyệt trước khi xác nhận.'
                ) % {
                    'name': picking.name,
                    'value': picking.internal_transfer_value,
                })
        return super().button_validate()

    def action_request_logistics_approval(self):
        for picking in self:
            picking.logistics_approval_state = (
                'to_approve' if picking.logistics_needs_approval else 'not_required')

    def action_approve_logistics(self):
        if not self.env.user.has_group('company_logistics.group_logistics_manager'):
            raise UserError(_('Chỉ quản lý kho mới được duyệt phiếu chuyển kho.'))
        for picking in self:
            picking.write({
                'logistics_approval_state': 'approved' if picking.logistics_needs_approval else 'not_required',
                'logistics_approver_id': self.env.user.id,
                'logistics_approval_date': fields.Datetime.now(),
            })

    def action_refuse_logistics(self):
        if not self.env.user.has_group('company_logistics.group_logistics_manager'):
            raise UserError(_('Chỉ quản lý kho mới được từ chối phiếu chuyển kho.'))
        self.write({
            'logistics_approval_state': 'refused',
            'logistics_approver_id': self.env.user.id,
            'logistics_approval_date': fields.Datetime.now(),
        })

    def _prepare_carrier_payload(self):
        self.ensure_one()
        return {
            'reference': self.name,
            'carrier': self.carrier_id.name,
            'customer': {
                'name': self.partner_id.name or '',
                'phone': self.partner_id.phone or '',
                'address': self.partner_id.contact_address or '',
            },
            'weight': self.weight,
            'items': [{
                'name': move.product_id.display_name,
                'quantity': move.product_uom_qty,
                'price': move.product_id.standard_price,
            } for move in self.move_ids],
        }

    def action_book_shipment(self):
        self.ensure_one()
        if not self.carrier_id:
            raise UserError(_('Chọn đơn vị vận chuyển trước khi tạo vận đơn.'))
        payload = self._prepare_carrier_payload()
        log = self.env['company.shipment.log'].create({
            'picking_id': self.id,
            'carrier_id': self.carrier_id.id,
            'request_payload': json.dumps(payload, ensure_ascii=False, indent=2),
            'state': 'draft',
        })
        carrier = self.carrier_id
        if not carrier.api_endpoint or not carrier.api_token:
            log.write({
                'state': 'manual',
                'message': 'Chưa cấu hình API endpoint/token. Vui lòng nhập mã vận đơn thủ công.',
            })
            return self._notify_shipment(log)
        try:
            response = requests.post(
                carrier.api_endpoint,
                json=payload,
                headers={
                    'Authorization': 'Bearer %s' % carrier.api_token,
                    'Token': carrier.api_token,
                    'Content-Type': 'application/json',
                },
                timeout=30,
            )
            text = response.text or ''
            log.write({
                'response_payload': text[:10000],
                'state': 'sent' if response.ok else 'error',
                'message': 'HTTP %s' % response.status_code,
            })
            if response.ok:
                tracking = self._extract_tracking_ref(text)
                if tracking:
                    log.tracking_ref = tracking
                    self.carrier_tracking_ref = tracking
        except Exception as exc:  # noqa: BLE001 - API vendors raise many exceptions
            _logger.exception('Carrier booking failed for %s', self.name)
            log.write({'state': 'error', 'message': str(exc)[:2000]})
        return self._notify_shipment(log)

    @api.model
    def _extract_tracking_ref(self, response_text):
        try:
            data = json.loads(response_text)
        except ValueError:
            return False
        if not isinstance(data, dict):
            return False
        for key in ('tracking_number', 'order_code', 'tracking_ref'):
            if data.get(key):
                return str(data[key])
        nested = data.get('data')
        if isinstance(nested, dict):
            for key in ('tracking_number', 'order_code', 'tracking_ref'):
                if nested.get(key):
                    return str(nested[key])
        return False

    def _notify_shipment(self, log):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tạo vận đơn'),
                'message': log.message or log.state,
                'type': 'success' if log.state == 'sent' else 'warning',
                'sticky': False,
            },
        }
