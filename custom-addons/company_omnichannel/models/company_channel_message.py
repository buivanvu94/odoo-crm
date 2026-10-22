from odoo import fields, models


class CompanyChannelMessage(models.Model):
    _name = 'company.channel.message'
    _description = 'Log tin nhắn omnichannel'
    _order = 'create_date desc, id desc'

    config_id = fields.Many2one(
        'company.channel.config', string='Kênh', required=True, ondelete='cascade')
    channel = fields.Selection(related='config_id.channel', store=True, string='Loại kênh')
    company_id = fields.Many2one(
        'res.company', related='config_id.company_id', store=True, string='Công ty')
    external_id = fields.Char(string='Mã ngoài')
    event_name = fields.Char(string='Sự kiện')
    state = fields.Selection(
        selection=[
            ('received', 'Đã nhận'),
            ('processed', 'Đã tạo lead'),
            ('error', 'Lỗi'),
        ],
        string='Trạng thái', default='received',
    )
    lead_id = fields.Many2one('crm.lead', string='Lead / Cơ hội', ondelete='set null')
    payload = fields.Text(string='Payload')
    error = fields.Text(string='Lỗi')
