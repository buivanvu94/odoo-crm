{
    'name': 'Company Logistics',
    'version': '20.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Duyệt chuyển kho nội bộ, cấu hình và tạo vận đơn',
    'description': """
Company Logistics
=================

* Duyệt phiếu chuyển kho nội bộ theo giá trị hàng hóa.
* Cấu hình đơn vị vận chuyển Việt Nam (GHN, Viettel Post, khác).
* Tạo vận đơn: gọi API nếu đã cấu hình endpoint/token, lưu log request/response.
* Theo dõi mã vận đơn trên phiếu kho.
    """,
    'author': 'My Company',
    'license': 'LGPL-3',
    'depends': ['stock_delivery'],
    'data': [
        'security/company_logistics_security.xml',
        'security/ir.access.csv',
        'views/res_config_settings_views.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_picking_views.xml',
        'views/company_shipment_log_views.xml',
    ],
    'installable': True,
}
