{
    'name': 'Company Payment Approval',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Duyệt phiếu chi / thanh toán vượt hạn mức',
    'description': """
Company Payment Approval
========================

* Đặt hạn mức thanh toán chi ra được tự động xác nhận.
* Phiếu chi vượt hạn mức phải được quản lý kế toán duyệt trước khi Confirm.
* Tự động đưa về trạng thái chờ duyệt khi sửa số tiền / đối tác / nhật ký.
* Có màn hình riêng theo dõi các phiếu đang chờ duyệt.
    """,
    'author': 'My Company',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/company_payment_approval_security.xml',
        'views/res_config_settings_views.xml',
        'views/account_payment_views.xml',
        'views/company_payment_approval_menus.xml',
    ],
    'installable': True,
}
