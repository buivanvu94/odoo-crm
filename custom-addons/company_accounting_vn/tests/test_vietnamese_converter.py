from datetime import date
from decimal import Decimal

from odoo.tests import BaseCase, tagged

from ..tools.vietnamese_converter import amount_to_words_vi, format_date_vi, number_to_words_vi


@tagged('post_install', '-at_install')
class TestVietnameseConverter(BaseCase):

    def test_amount_to_words(self):
        cases = {
            0: 'Không đồng chẵn',
            1: 'Một đồng chẵn',
            5: 'Năm đồng chẵn',
            10: 'Mười đồng chẵn',
            11: 'Mười một đồng chẵn',
            14: 'Mười bốn đồng chẵn',
            15: 'Mười lăm đồng chẵn',
            20: 'Hai mươi đồng chẵn',
            21: 'Hai mươi mốt đồng chẵn',
            24: 'Hai mươi tư đồng chẵn',
            25: 'Hai mươi lăm đồng chẵn',
            44: 'Bốn mươi tư đồng chẵn',
            100: 'Một trăm đồng chẵn',
            101: 'Một trăm lẻ một đồng chẵn',
            105: 'Một trăm lẻ năm đồng chẵn',
            110: 'Một trăm mười đồng chẵn',
            115: 'Một trăm mười lăm đồng chẵn',
            1000: 'Một nghìn đồng chẵn',
            1005: 'Một nghìn không trăm lẻ năm đồng chẵn',
            1010: 'Một nghìn không trăm mười đồng chẵn',
            105000: 'Một trăm lẻ năm nghìn đồng chẵn',
            1000000: 'Một triệu đồng chẵn',
            1000005: 'Một triệu không trăm lẻ năm đồng chẵn',
            1005000: 'Một triệu không trăm lẻ năm nghìn đồng chẵn',
            15420000: 'Mười lăm triệu bốn trăm hai mươi nghìn đồng chẵn',
            1000000000: 'Một tỷ đồng chẵn',
            2345678901: 'Hai tỷ ba trăm bốn mươi lăm triệu sáu trăm bảy mươi tám nghìn chín trăm lẻ một đồng chẵn',
            1000000000000: 'Một nghìn tỷ đồng chẵn',
            1001000000000: 'Một nghìn không trăm lẻ một tỷ đồng chẵn',
            1000000000005: 'Một nghìn tỷ không trăm lẻ năm đồng chẵn',
            15000000000000: 'Mười lăm nghìn tỷ đồng chẵn',
            10 ** 15: 'Một triệu tỷ đồng chẵn',
            10 ** 18: 'Một tỷ tỷ đồng chẵn',
            10 ** 18 + 1001 * 10 ** 9 + 5: 'Một tỷ tỷ không trăm lẻ một nghìn không trăm lẻ một tỷ không trăm lẻ năm đồng chẵn',
            10 ** 21: 'Một nghìn tỷ tỷ đồng chẵn',
            -15000: 'Âm mười lăm nghìn đồng chẵn',
        }
        for amount, expected in cases.items():
            with self.subTest(amount=amount):
                self.assertEqual(amount_to_words_vi(amount), expected)

    def test_rounding_and_types(self):
        self.assertEqual(amount_to_words_vi(1000.5), 'Một nghìn không trăm lẻ một đồng chẵn')
        self.assertEqual(amount_to_words_vi(Decimal('999.4')), 'Chín trăm chín mươi chín đồng chẵn')
        self.assertEqual(amount_to_words_vi(0.4), 'Không đồng chẵn')

    def test_linh_variant(self):
        self.assertEqual(number_to_words_vi(1005, linh=True), 'một nghìn không trăm linh năm')

    def test_too_large(self):
        with self.assertRaises(ValueError):
            number_to_words_vi(10 ** 27)

    def test_date(self):
        self.assertEqual(format_date_vi(date(2026, 3, 5)), 'Ngày 05 tháng 03 năm 2026')
        self.assertEqual(format_date_vi(), 'Ngày ... tháng ... năm ...')
