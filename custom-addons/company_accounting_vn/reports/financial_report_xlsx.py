"""Xuất báo cáo tài chính ra Excel (mỗi báo cáo một sheet) bằng xlsxwriter."""
import io

import xlsxwriter


def build_xlsx(sections, company_name):
    """``sections`` là danh sách kết quả của ``vn.financial.report.build``; trả về nội dung .xlsx (bytes)."""
    buffer = io.BytesIO()
    book = xlsxwriter.Workbook(buffer, {'in_memory': True})
    title = book.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
    head = book.add_format({'bold': True, 'border': 1, 'bg_color': '#D9D9D9', 'align': 'center', 'text_wrap': True})
    text = {bold: book.add_format({'border': 1, 'bold': bold}) for bold in (False, True)}
    money = {bold: book.add_format({'border': 1, 'bold': bold, 'num_format': '#,##0;[Red]-#,##0'})
             for bold in (False, True)}
    for section in sections:
        sheet = book.add_worksheet(section['form_code'])  # một bộ báo cáo chỉ có một B03
        last_col = 3 if section['has_prior'] else 2
        sheet.write(0, 0, company_name)
        sheet.write(1, 0, 'Mẫu số %s' % section['form_code'])
        sheet.merge_range(2, 0, 2, last_col, section['title'], title)
        sheet.merge_range(3, 0, 3, last_col, section['date_text'], title)
        headers = ['Chỉ tiêu', 'Mã số', 'Số kỳ này'] + (['Số kỳ so sánh'] if section['has_prior'] else [])
        for col, header in enumerate(headers):
            sheet.write(5, col, header, head)
        sheet.set_column(0, 0, 70)
        sheet.set_column(1, 1, 8)
        sheet.set_column(2, last_col, 20)
        for offset, row in enumerate(section['rows']):
            line, bold = 6 + offset, row['bold']
            sheet.write_string(line, 0, '    ' * row['level'] + row['name'], text[bold])
            sheet.write_string(line, 1, row['code'], text[bold])
            for col, key in ((2, 'value'), (3, 'prior')):
                if col > last_col:
                    break
                if row[key] is None:
                    sheet.write_blank(line, col, None, text[bold])
                else:
                    sheet.write_number(line, col, row[key], money[bold])
        sheet.freeze_panes(6, 0)
    book.close()
    return buffer.getvalue()
