{
    'name': 'Vietnam Accounting (TT 99/2025)',
    'version': '20.0.1.1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'summary': 'Kế toán doanh nghiệp Việt Nam: TT 99/2025, tài khoản đối ứng, phiếu thu/chi/nhập/xuất',
    'description': """
Vietnam Accounting (TT 99/2025/TT-BTC)
======================================

* Chart template ``vn_tt99`` (71 tài khoản cấp 1 theo Thông tư 99/2025/TT-BTC),
  kế thừa dữ liệu thuế GTGT của ``l10n_vn``.
* Tài khoản đối ứng (Nợ TK / Có TK) trên từng dòng bút toán khi ghi sổ.
* Chặn ghi sổ khi TK 131/331/141 thiếu đối tượng (partner).
* Trường hóa đơn điện tử theo NĐ 254/2026/NĐ-CP, nối chế độ chạy thử của company_einvoice.
* Mẫu in Phiếu thu 01-TT, Phiếu chi 02-TT, Phiếu nhập 01-VT, Phiếu xuất 02-VT.
    """,
    'author': 'My Company',
    'license': 'LGPL-3',
    'application': False,
    'depends': [
        'account',
        'l10n_vn',
        'stock',
        'stock_account',
        'company_einvoice',
        'company_payment_approval',
    ],
    'data': [
        'security/ir.access.csv',
        'data/report_paperformat.xml',
        'views/res_company_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'reports/report_voucher_common.xml',
        'reports/report_payment_receipt.xml',
        'reports/report_payment_voucher.xml',
        'reports/report_stock_in_out.xml',
        'wizards/accounting_report_wizard_views.xml',
        'reports/ledger_report.xml',
        'data/vn.financial.report.line.csv',
        'reports/financial_report_templates.xml',
        'wizards/financial_report_wizard_views.xml',
        # Các phần mở rộng (sổ sách, báo cáo tài chính) thêm tiếp ở dưới.
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
}
