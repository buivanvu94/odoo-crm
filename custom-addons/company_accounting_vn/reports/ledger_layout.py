"""Khai báo loại sổ, tiêu đề, mẫu số và cột hiển thị. Dùng chung cho màn hình, PDF và Excel."""

REPORT_TYPES = [
    ('journal', 'Sổ Nhật ký chung (S01-DN)'),
    ('ledger', 'Sổ Cái (S02b-DN)'),
    ('cash', 'Sổ quỹ tiền mặt (S07-DN)'),
    ('bank', 'Sổ tiền gửi ngân hàng (S08-DN)'),
    ('partner_131', 'Sổ chi tiết công nợ phải thu 131 (S31-DN)'),
    ('partner_331', 'Sổ chi tiết công nợ phải trả 331 (S31-DN)'),
    ('trial', 'Bảng cân đối số phát sinh các tài khoản'),
]

TITLES = dict(REPORT_TYPES)

# Tiền tố TK chính của từng loại sổ.
BOOK_PREFIX = {'cash': '111', 'bank': '112', 'partner_131': '131', 'partner_331': '331'}

FORM_CODES = {
    'journal': 'S01 - DN', 'ledger': 'S02b - DN', 'cash': 'S07 - DN', 'bank': 'S08 - DN',
    'partner_131': 'S31 - DN', 'partner_331': 'S31 - DN', 'trial': '',
}

# (khóa trong dòng dữ liệu, tiêu đề cột, là cột tiền)
_DATE = ('date', 'Ngày ghi sổ', False)
_VOUCHER = ('voucher', 'Số chứng từ', False)
_LABEL = ('label', 'Diễn giải', False)
_ACCOUNT = ('account', 'TK', False)
_COUNTERPART = ('counterpart', 'TK đối ứng', False)
_PARTNER = ('partner', 'Đối tượng', False)
_JOURNAL = ('journal', 'Sổ NK', False)
_MOVEMENT = [('debit', 'Phát sinh Nợ', True), ('credit', 'Phát sinh Có', True)]
_BALANCE = [('bal_debit', 'Dư Nợ', True), ('bal_credit', 'Dư Có', True)]

COLUMNS = {
    'journal': [_DATE, _VOUCHER, _LABEL, _ACCOUNT, _COUNTERPART, _PARTNER, _JOURNAL] + _MOVEMENT,
    'ledger': [_DATE, _VOUCHER, _LABEL, _COUNTERPART, _PARTNER] + _MOVEMENT + _BALANCE,
    'cash': [_DATE, _VOUCHER, _LABEL, _COUNTERPART, _PARTNER, _JOURNAL,
             ('debit', 'Thu (Nợ)', True), ('credit', 'Chi (Có)', True)] + _BALANCE,
    'partner_131': [_DATE, _VOUCHER, _LABEL, _ACCOUNT, _COUNTERPART] + _MOVEMENT + _BALANCE,
    'trial': [
        _ACCOUNT, ('label', 'Tên tài khoản', False),
        ('open_debit', 'Dư Nợ đầu kỳ', True), ('open_credit', 'Dư Có đầu kỳ', True),
        ('debit', 'Phát sinh Nợ', True), ('credit', 'Phát sinh Có', True),
        ('close_debit', 'Dư Nợ cuối kỳ', True), ('close_credit', 'Dư Có cuối kỳ', True),
    ],
}
COLUMNS['bank'] = COLUMNS['cash']
COLUMNS['partner_331'] = COLUMNS['partner_131']
