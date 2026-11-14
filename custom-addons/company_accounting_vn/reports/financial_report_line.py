"""Chỉ tiêu (dòng) của bộ báo cáo tài chính: mã số, tên và công thức nạp từ data/vn.financial.report.line.csv.

Công thức là chuỗi các số hạng cộng/trừ, mỗi số hạng là một trong hai dạng:

* ``HÀM(tiền_tố_tk, ...)``: lấy số liệu theo mã tài khoản hiển thị (``vn_display_code``) bắt đầu bằng tiền tố.
  ``*`` là mọi tài khoản, ``!tiền_tố`` loại trừ, ``@cash`` / ``@cash_equivalent`` / ``@suspense`` là tiền,
  tương đương tiền, TK treo của sổ nhật ký tiền / ngân hàng (TK treo không thuộc tiền dù mã là 1121). Các hàm:

  ======  ============================================================================
  DB/CB   số dư Nợ / số dư Có cuối kỳ, tính riêng từng tài khoản rồi cộng (phần dương)
  ND/NC   số dư Nợ - Có / Có - Nợ lũy kế đến cuối kỳ (có dấu)
  OD      số dư Nợ - Có đầu kỳ (trước ngày bắt đầu)
  DM/CM   phát sinh Nợ / phát sinh Có trong kỳ (không tính bút toán kết chuyển TK 911)
  NM      phát sinh Có - Nợ trong kỳ
  CI/CO   tiền thu vào / chi ra trong kỳ, theo tài khoản đối ứng của bút toán có động tiền
  ======  ============================================================================

* ``[mã]`` hoặc ``[loại_báo_cáo:mã]``: giá trị của chỉ tiêu khác (tổng hợp chỉ tiêu cha, tham chiếu chéo báo cáo).
"""
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

FUNCTIONS = ('DB', 'CB', 'ND', 'NC', 'OD', 'DM', 'CM', 'NM', 'CI', 'CO')
_TERM = re.compile(r'\s*(?P<sign>[+-]?)\s*(?:(?P<fn>[A-Z]{2})\((?P<arg>[^)]*)\)|\[(?P<ref>\w+(?::\w+)?)\])\s*')

REPORT_TYPES = [
    ('b01', 'B01-DN Báo cáo tình hình tài chính'),
    ('b02', 'B02-DN Báo cáo kết quả hoạt động kinh doanh'),
    ('b03d', 'B03-DN Báo cáo lưu chuyển tiền tệ (trực tiếp)'),
    ('b03i', 'B03-DN Báo cáo lưu chuyển tiền tệ (gián tiếp)'),
]


def parse_formula(text):
    """Tách công thức thành danh sách ``(dấu, hàm, đối_số, tham_chiếu)``; ném ValueError nếu sai cú pháp."""
    terms, pos = [], 0
    text = text or ''
    while pos < len(text):
        match = _TERM.match(text, pos)
        if not match or match.end() == pos:
            raise ValueError(text[pos:])
        fn = match.group('fn')
        if fn and fn not in FUNCTIONS:
            raise ValueError(fn)
        terms.append((match.group('sign') or '+', fn, match.group('arg'), match.group('ref')))
        pos = match.end()
    return terms


class VnFinancialReportLine(models.Model):
    _name = 'vn.financial.report.line'
    _description = 'Financial statement line (TT 99 Appendix IV)'
    _order = 'report_type, sequence, id'

    report_type = fields.Selection(REPORT_TYPES, required=True, index=True)
    sequence = fields.Integer(default=10)
    code = fields.Char(string='Line Code', help='Mã số chỉ tiêu; để trống với dòng tiêu đề.')
    name = fields.Char(required=True, translate=True)
    level = fields.Integer(default=0, help='Mức thụt lề khi hiển thị.')
    bold = fields.Boolean()
    formula = fields.Text(help='Xem phần mô tả đầu file reports/financial_report_line.py.')

    _code_uniq = models.Constraint('UNIQUE(report_type, code)', 'Line code must be unique per report.')

    @api.constrains('formula')
    def _check_formula(self):
        for line in self:
            try:
                parse_formula(line.formula)
            except ValueError as error:
                raise ValidationError(
                    self.env._('Invalid formula on line %(code)s near "%(rest)s".', code=line.code, rest=error)
                ) from error
