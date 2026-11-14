"""Xuất sổ kế toán ra Excel bằng xlsxwriter (có sẵn trong Odoo) từ dữ liệu của ``vn.ledger.engine``."""
import io

import xlsxwriter

BOLD_KINDS = ('group', 'open', 'total', 'close', 'grand')


def build_xlsx(data, company_name):
    """Trả về nội dung file .xlsx (bytes). ``data`` là kết quả ``vn.ledger.engine.build``."""
    buffer = io.BytesIO()
    book = xlsxwriter.Workbook(buffer, {'in_memory': True})
    sheet = book.add_worksheet(data['title'][:31].replace('/', '-'))
    title = book.add_format({'bold': True, 'font_size': 14})
    head = book.add_format({'bold': True, 'border': 1, 'bg_color': '#D9D9D9', 'text_wrap': True, 'align': 'center'})
    fmt = {}
    for bold in (False, True):
        fmt[bold, False] = book.add_format({'border': 1, 'bold': bold})
        fmt[bold, True] = book.add_format({'border': 1, 'bold': bold, 'num_format': '#,##0.00'})
    columns = data['columns']
    sheet.write(0, 0, company_name)
    sheet.write(1, 0, ('Mẫu số %s' % data['form_code']) if data['form_code'] else '')
    sheet.write(2, 0, data['title'].upper(), title)
    sheet.write(3, 0, data['period'])
    for idx, (_key, header, _money) in enumerate(columns):
        sheet.write(5, idx, header, head)
        sheet.set_column(idx, idx, 16 if _money else 22)
    for offset, row in enumerate(data['rows']):
        bold = row['kind'] in BOLD_KINDS
        for idx, (key, _header, money) in enumerate(columns):
            value = row.get(key)
            if money:
                sheet.write_number(6 + offset, idx, value or 0.0, fmt[bold, True])
            else:
                sheet.write_string(6 + offset, idx, value or '', fmt[bold, False])
    sheet.freeze_panes(6, 0)
    book.close()
    return buffer.getvalue()
