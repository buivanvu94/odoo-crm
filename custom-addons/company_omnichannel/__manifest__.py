{
    'name': 'Company Omnichannel',
    'version': '20.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Nhận lead từ Zalo OA, Facebook và website vào CRM',
    'description': """
Company Omnichannel
===================

* Cấu hình kênh Zalo OA, Facebook, website.
* Webhook xác thực (Facebook hub.challenge) và nhận sự kiện.
* Tự động tạo lead/cơ hội trong CRM, gán team, nhân viên, nguồn.
* Lưu log payload nhận được để kiểm tra và đối soát.
* Endpoint website: POST JSON {name, phone, email, message}.
    """,
    'author': 'My Company',
    'license': 'LGPL-3',
    'depends': ['crm'],
    'data': [
        'security/company_omnichannel_security.xml',
        'security/ir.access.csv',
        'views/company_channel_config_views.xml',
        'views/company_channel_message_views.xml',
        'views/company_omnichannel_menus.xml',
    ],
    'installable': True,
}
