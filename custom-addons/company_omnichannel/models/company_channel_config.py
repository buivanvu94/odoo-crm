import json
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

CHANNEL_LABELS = {
    'zalo': 'Zalo OA',
    'facebook': 'Facebook',
    'website': 'Website',
}


class CompanyChannelConfig(models.Model):
    _name = 'company.channel.config'
    _description = 'Cấu hình kênh omnichannel'
    _order = 'name'

    name = fields.Char(string='Tên kênh', required=True)
    channel = fields.Selection(
        selection=[
            ('zalo', 'Zalo OA'),
            ('facebook', 'Facebook'),
            ('website', 'Website'),
        ],
        string='Kênh', required=True, default='website',
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty', required=True,
        default=lambda self: self.env.company)
    verify_token = fields.Char(
        string='Verify Token',
        help='Dùng cho bước xác thực webhook Facebook (hub.verify_token).',
    )
    app_id = fields.Char(string='App ID')
    app_secret = fields.Char(string='App Secret')
    page_id = fields.Char(string='Page / OA ID')
    access_token = fields.Char(string='Access Token')
    default_team_id = fields.Many2one('crm.team', string='Team mặc định')
    default_user_id = fields.Many2one(
        'res.users', string='Nhân viên phụ trách',
        domain="[('share', '=', False)]")
    source_id = fields.Many2one('utm.source', string='Nguồn mặc định')
    note = fields.Text(string='Ghi chú')
    webhook_url = fields.Char(string='Webhook URL', compute='_compute_urls')
    verify_url = fields.Char(string='Verify URL', compute='_compute_urls')

    def _compute_urls(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for config in self:
            config.webhook_url = '%s/company/omnichannel/webhook/%s' % (base, config.id or '')
            config.verify_url = '%s/company/omnichannel/verify/%s' % (base, config.id or '')

    def _channel_label(self):
        self.ensure_one()
        return CHANNEL_LABELS.get(self.channel, self.name)

    @staticmethod
    def _field_value(field_data, names):
        for item in field_data or []:
            if item.get('name') in names:
                values = item.get('values') or []
                return values[0] if values else ''
        return ''

    def _extract_info(self, data):
        self.ensure_one()
        data = data or {}
        info = {
            'external_id': '',
            'contact_name': '',
            'phone': '',
            'email': '',
            'message': '',
            'event_name': '',
        }
        if self.channel == 'zalo':
            sender = data.get('sender') or {}
            message = data.get('message') or {}
            info.update({
                'external_id': str(sender.get('id') or data.get('user_id') or ''),
                'contact_name': sender.get('name') or data.get('sender_name') or '',
                'phone': sender.get('phone') or '',
                'email': sender.get('email') or '',
                'message': message.get('text') if isinstance(message, dict) else str(message),
                'event_name': data.get('event_name') or 'message',
            })
        elif self.channel == 'facebook':
            for entry in data.get('entry') or []:
                for change in entry.get('changes') or []:
                    value = change.get('value') or {}
                    if value.get('leadgen_id'):
                        field_data = value.get('field_data') or []
                        info.update({
                            'external_id': str(value.get('leadgen_id')),
                            'contact_name': self._field_value(field_data, ('full_name', 'name')),
                            'phone': self._field_value(field_data, ('phone_number', 'phone')),
                            'email': self._field_value(field_data, ('email',)),
                            'message': self._field_value(field_data, ('message', 'custom_question')),
                            'event_name': 'leadgen',
                        })
                        return info
                for messaging in entry.get('messaging') or []:
                    sender = messaging.get('sender') or {}
                    message = messaging.get('message') or {}
                    info.update({
                        'external_id': str(sender.get('id') or ''),
                        'contact_name': sender.get('name') or '',
                        'message': message.get('text') or '',
                        'event_name': 'message',
                    })
                    return info
            info.update({
                'external_id': str(data.get('leadgen_id') or data.get('sender_id') or ''),
                'contact_name': data.get('name') or '',
                'phone': data.get('phone') or '',
                'email': data.get('email') or '',
                'message': data.get('message') or '',
                'event_name': data.get('event_name') or 'message',
            })
        else:
            info.update({
                'external_id': str(data.get('external_id') or ''),
                'contact_name': data.get('name') or data.get('full_name') or '',
                'phone': data.get('phone') or data.get('phone_number') or '',
                'email': data.get('email') or '',
                'message': data.get('message') or data.get('content') or '',
                'event_name': data.get('event_name') or 'website_form',
            })
        return info

    def _get_source(self):
        self.ensure_one()
        if self.source_id:
            return self.source_id
        name = self._channel_label()
        source = self.env['utm.source'].sudo().search([('name', '=', name)], limit=1)
        return source or self.env['utm.source'].sudo().create({'name': name})

    def _process_payload(self, data):
        self.ensure_one()
        data = data or {}
        info = self._extract_info(data)
        label = self._channel_label()
        log = self.env['company.channel.message'].sudo().create({
            'config_id': self.id,
            'external_id': info.get('external_id') or False,
            'event_name': info.get('event_name') or False,
            'payload': json.dumps(data, ensure_ascii=False, indent=2),
            'state': 'received',
        })
        name = info.get('contact_name') or info.get('external_id') or _('Khách mới')
        description_parts = [
            _('Kênh: %s') % label,
            _('Sự kiện: %s') % (info.get('event_name') or ''),
            _('Mã ngoài: %s') % (info.get('external_id') or ''),
        ]
        if info.get('message'):
            description_parts.append('\n' + str(info['message']))
        lead_vals = {
            'name': '%s - %s' % (label, name),
            'contact_name': info.get('contact_name') or False,
            'phone': info.get('phone') or False,
            'email_from': info.get('email') or False,
            'description': '\n'.join(description_parts),
            'type': 'lead',
            'company_id': self.company_id.id,
            'source_id': self._get_source().id,
        }
        if self.default_team_id:
            lead_vals['team_id'] = self.default_team_id.id
        if self.default_user_id:
            lead_vals['user_id'] = self.default_user_id.id
        try:
            lead = self.env['crm.lead'].sudo().create(lead_vals)
        except Exception as exc:  # noqa: BLE001 - never fail the webhook
            _logger.exception('Omnichannel lead creation failed for %s', self.name)
            log.write({'state': 'error', 'error': str(exc)[:2000]})
            return self.env['crm.lead'], log
        log.write({'state': 'processed', 'lead_id': lead.id})
        return lead, log
