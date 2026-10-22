import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


class OmnichannelController(http.Controller):

    @http.route('/company/omnichannel/verify/<int:config_id>', type='http',
                auth='public', csrf=False, methods=['GET'], save_session=False)
    def verify_webhook(self, config_id, **kwargs):
        config = request.env['company.channel.config'].sudo().browse(config_id).exists()
        if not config or not config.active:
            return Response('Not found', status=404)
        token = kwargs.get('hub.verify_token') or kwargs.get('verify_token')
        challenge = kwargs.get('hub.challenge') or kwargs.get('challenge') or ''
        if config.verify_token and token == config.verify_token:
            return Response(challenge, content_type='text/plain')
        return Response('Forbidden', status=403)

    @http.route('/company/omnichannel/webhook/<int:config_id>', type='http',
                auth='public', csrf=False, methods=['POST'], save_session=False)
    def receive_webhook(self, config_id, **kwargs):
        config = request.env['company.channel.config'].sudo().browse(config_id).exists()
        if not config or not config.active:
            return self._json({'ok': False, 'error': 'not_found'}, status=404)
        raw_body = request.httprequest.get_data() or b''
        if not self._check_facebook_signature(config, raw_body):
            return self._json({'ok': False, 'error': 'bad_signature'}, status=403)
        try:
            data = json.loads(raw_body.decode('utf-8')) if raw_body else dict(kwargs)
        except (ValueError, UnicodeDecodeError):
            data = dict(kwargs)
        lead, log = config._process_payload(data)
        return self._json({
            'ok': log.state != 'error',
            'lead_id': lead.id if lead else False,
            'message_id': log.id,
        }, status=200)

    def _check_facebook_signature(self, config, raw_body):
        if config.channel != 'facebook' or not config.app_secret:
            return True
        signature = request.httprequest.headers.get('X-Hub-Signature-256')
        if not signature:
            return True
        expected = 'sha256=' + hmac.new(
            config.app_secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _json(self, payload, status=200):
        return Response(
            json.dumps(payload, ensure_ascii=False),
            status=status,
            content_type='application/json',
        )
