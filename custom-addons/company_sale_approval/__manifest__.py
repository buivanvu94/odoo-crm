{
    'name': 'Company Sale Approval',
    'version': '20.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Duyệt chiết khấu và giá bán trên báo giá / đơn bán',
    'description': """
Company Sale Approval
=====================

* Giới hạn chiết khấu tối đa theo công ty.
* Chặn xác nhận báo giá khi chiết khấu vượt mức hoặc bán dưới giá vốn.
* Quy trình: Yêu cầu duyệt -> Duyệt / Từ chối -> Xác nhận đơn.
* Tự động reset trạng thái duyệt khi sửa dòng hàng.
    """,
    'author': 'My Company',
    'license': 'LGPL-3',
    'depends': ['sale_management'],
    'data': [
        'security/company_sale_approval_security.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/company_sale_approval_menus.xml',
    ],
    'installable': True,
}
