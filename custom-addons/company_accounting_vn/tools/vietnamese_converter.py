"""Tiện ích tiếng Việt cho chứng từ kế toán: số tiền thành chữ, ngày tháng."""
from decimal import ROUND_HALF_UP, Decimal

_DIGITS = ('không', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín')
# Tên hàng nhóm 3 chữ số trong một khối 9 chữ số: 10^0, 10^3, 10^6. Khối thứ k (10^(9k)) thêm "tỷ" k lần.
_UNITS = ('', 'nghìn', 'triệu')
_BLOCK = 10 ** 9
_MAX_BLOCKS = 3  # < 10^27 (đến "nghìn tỷ tỷ")


def _read_group(number, full, linh):
    """Đọc một nhóm 0..999. ``full``: nhóm đứng sau nhóm lớn hơn nên đọc đủ "không trăm"."""
    hundreds, tens, units = number // 100, number // 10 % 10, number % 10
    words = []
    if hundreds or full:
        words.append('%s trăm' % _DIGITS[hundreds])
    if tens > 1:
        words.append('%s mươi' % _DIGITS[tens])
    elif tens == 1:
        words.append('mười')
    elif units and (hundreds or full):
        words.append('linh' if linh else 'lẻ')
    if units:
        if units == 1 and tens > 1:
            words.append('mốt')
        elif units == 5 and tens >= 1:
            words.append('lăm')
        elif units == 4 and tens > 1:
            words.append('tư')
        else:
            words.append(_DIGITS[units])
    return ' '.join(words)


def number_to_words_vi(number, linh=False):
    """Đọc số nguyên thành chữ tiếng Việt (chữ thường). ``linh=True`` đọc "linh" thay cho "lẻ"."""
    number = int(number)
    if number == 0:
        return _DIGITS[0]
    if number < 0:
        return 'âm ' + number_to_words_vi(-number, linh)
    blocks = []
    while number:
        blocks.append(number % _BLOCK)
        number //= _BLOCK
    if len(blocks) > _MAX_BLOCKS:
        raise ValueError('Số quá lớn để đọc thành chữ.')
    words = []
    for index in range(len(blocks) - 1, -1, -1):
        if blocks[index]:
            words.append(_read_block(blocks[index], linh, is_top=index == len(blocks) - 1, billions=index))
    return ' '.join(words)


def _read_block(block, linh, is_top, billions):
    """Đọc một khối 9 chữ số (< 10^9) rồi thêm "tỷ" ``billions`` lần; khối đầu của số không đọc "không trăm" ở nhóm đầu."""
    parts = (block // 10 ** 6, block // 1000 % 1000, block % 1000)
    lead = next(i for i, part in enumerate(parts) if part)
    words = [
        ' '.join(filter(None, (_read_group(part, not is_top or i > lead, linh), _UNITS[2 - i])))
        for i, part in enumerate(parts) if part]
    return ' '.join(words + ['tỷ'] * billions)


def amount_to_words_vi(amount, unit='đồng', suffix='chẵn', linh=False):
    """Số tiền VND thành chữ, ví dụ 15420000 -> "Mười lăm triệu bốn trăm hai mươi nghìn đồng chẵn".

    Số tiền được làm tròn về đồng (VND không có đơn vị lẻ).
    """
    rounded = int(Decimal(str(amount)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    words = number_to_words_vi(rounded, linh)
    text = ' '.join(filter(None, (words, unit, suffix)))
    return text[0].upper() + text[1:]


def format_date_vi(date=None):
    """"Ngày 05 tháng 03 năm 2026"; không có ngày thì để chỗ trống để viết tay."""
    if not date:
        return 'Ngày ... tháng ... năm ...'
    return 'Ngày %02d tháng %02d năm %d' % (date.day, date.month, date.year)
