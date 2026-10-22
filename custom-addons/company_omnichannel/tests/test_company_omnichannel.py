from odoo.tests.common import TransactionCase


class TestOmnichannel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['company.channel.config'].create({
            'name': 'Website Test',
            'channel': 'website',
        })
        cls.zalo = cls.env['company.channel.config'].create({
            'name': 'Zalo Test',
            'channel': 'zalo',
        })
        cls.facebook = cls.env['company.channel.config'].create({
            'name': 'Facebook Test',
            'channel': 'facebook',
            'verify_token': 'test-token',
        })

    def test_website_creates_lead(self):
        lead, log = self.website._process_payload({
            'name': 'Nguyen Van A',
            'phone': '0900000000',
            'email': 'a@example.com',
            'message': 'Can tu van',
        })
        self.assertTrue(lead)
        self.assertEqual(lead.name, 'Website - Nguyen Van A')
        self.assertEqual(lead.phone, '0900000000')
        self.assertEqual(log.state, 'processed')
        self.assertEqual(log.lead_id, lead)

    def test_zalo_payload(self):
        lead, log = self.zalo._process_payload({
            'event_name': 'user_send_text',
            'sender': {'id': 'zalo-123', 'name': 'Tran B'},
            'message': {'text': 'Xin chao'},
        })
        self.assertTrue(lead)
        self.assertEqual(lead.contact_name, 'Tran B')
        self.assertIn('Xin chao', lead.description)
        self.assertEqual(log.external_id, 'zalo-123')

    def test_facebook_leadgen_payload(self):
        lead, log = self.facebook._process_payload({
            'entry': [{
                'changes': [{
                    'value': {
                        'leadgen_id': 'fb-999',
                        'field_data': [
                            {'name': 'full_name', 'values': ['Le C']},
                            {'name': 'phone_number', 'values': ['0911111111']},
                            {'name': 'email', 'values': ['c@example.com']},
                        ],
                    },
                }],
            }],
        })
        self.assertTrue(lead)
        self.assertEqual(lead.contact_name, 'Le C')
        self.assertEqual(lead.phone, '0911111111')
        self.assertEqual(log.external_id, 'fb-999')
