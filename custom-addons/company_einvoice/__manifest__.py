{
    'name': 'Company E-Invoice',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Kết nối hóa đơn điện tử VNPT / nhà cung cấp tùy chỉnh',
    'description': """
Company E-Invoice
=================

* Cấu hình nhà cung cấp hóa đơn điện tử (VNPT, Viettel qua module core
  l10n_vn_edi_viettel, hoặc API tùy chỉnh).
* Tạo payload hóa đơn từ account.move.
* Gửi hóa đơn qua API, lưu request/response, mã hóa đơn và trạng thái.
* Chế độ "chạy thử" để kiểm tra payload khi chưa có tài khoản thật.

Lưu ý: cần endpoint/token do VNPT hoặc Viettel cấp để gửi thật.
    """,
    'author': 'My Company',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/company_einvoice_security.xml',
        'security/ir.access.csv',
        'views/company_einvoice_provider_views.xml',
        'views/account_move_views.xml',
        'views/company_einvoice_menus.xml',
    ],
    'installable': True,
}
