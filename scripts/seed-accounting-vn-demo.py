# Nạp dữ liệu kế toán mẫu (Q4/2026) cho module company_accounting_vn.
# Chạy:  cd odoo && ../.venv/bin/python odoo-bin shell -c odoo.conf -d <DB> < ../scripts/seed-accounting-vn-demo.py
# Yêu cầu: công ty đang dùng chart `vn_tt99`, chưa có bút toán. Idempotent: bỏ qua nếu đã seed.
# Ghi vào DB thật => luôn backup trước (pg_dump) khi chạy.
from datetime import date

from odoo import Command

env = env(user=2)  # admin: có nhóm kế toán trưởng
co = env.company
assert co.chart_template == 'vn_tt99', 'Công ty chưa dùng chart vn_tt99'
if env['res.partner'].search_count([('ref', '=', 'SEED-VN')]):
    print('SEED: đã nạp trước đó, bỏ qua')
    raise SystemExit(0)

# --- tra cứu TK theo mã hiển thị (vn_display_code), thuế theo loại + thuế suất ---------
ACC = {}
for a in env['account.account'].search([('company_ids', 'in', co.id)], order='code'):
    ACC.setdefault(a.vn_display_code, a)


def acc(code):
    return ACC[code]


def tax(use, pct):
    cands = env['account.tax'].search([('type_tax_use', '=', use), ('amount', '=', pct), ('company_id', '=', co.id)])
    cands = cands.filtered(lambda t: not any(w in t.name.lower() for w in ('non', 'exempt', 'imported')))
    return cands[:1]


def journal(code):
    return env['account.journal'].search([('code', '=', code), ('company_id', '=', co.id)], limit=1)


def partner(name, street, vat, ref='', supplier=False):
    return env['res.partner'].create({
        'name': name, 'street': street, 'vat': vat, 'ref': ref, 'is_company': True,
        'country_id': env.ref('base.vn').id,
    })


D = lambda m, d: date(2026, m, d)  # noqa: E731

# --- đối tác ---------------------------------------------------------------------------
c1 = partner('Công ty TNHH Thương mại Sao Việt', '25 Nguyễn Huệ, Q.1, TP.HCM', '0312345678', 'SEED-VN')
c2 = partner('Công ty CP Công nghệ Hoàng Long', '88 Cầu Giấy, Hà Nội', '0108765432')
c3 = partner('Siêu thị Minh Châu', '120 Lê Duẩn, Đà Nẵng', '0401234567')
c4 = partner('Công ty TNHH Xây dựng An Phát', '14 Trần Hưng Đạo, Cần Thơ', '1801122334')
c5 = partner('Nhà hàng Hương Việt', '5 Phạm Ngũ Lão, Q.1, TP.HCM', '0309988776')
s1 = partner('Công ty CP Phân phối Tân Thịnh', '300 Điện Biên Phủ, Q.3, TP.HCM', '0305544332')
s2 = partner('Công ty CP Thiết bị Máy tính Phong Vũ', '1 Nguyễn Thị Minh Khai, Q.1, TP.HCM', '0302211443')
s3 = partner('Công ty TNHH Bất động sản Phú Gia', '9 Võ Văn Tần, Q.3, TP.HCM', '0316677889')
s4 = partner('Tổng Công ty Điện lực TP.HCM', '45 Đinh Tiên Hoàng, Q.1, TP.HCM', '0300951119')
s5 = partner('Công ty TNHH Văn phòng phẩm Hồng Hà', '7 Hàng Bài, Hà Nội', '0100112233')
s6 = partner('Công ty TNHH Truyền thông Việt Quảng', '60 Nguyễn Đình Chiểu, Q.3, TP.HCM', '0314455667')


def line(name, qty, price, tax_rec, account=None):
    vals = {'name': name, 'quantity': qty, 'price_unit': price, 'tax_ids': [Command.set(tax_rec.ids)]}
    if account:
        vals['account_id'] = account.id
    return Command.create(vals)


def post_move(kind, prt, dt, lines, ref='', journal_code=None):
    vals = {'move_type': kind, 'partner_id': prt.id, 'invoice_date': dt, 'date': dt,
            'invoice_line_ids': lines, 'ref': ref}
    if journal_code:
        vals['journal_id'] = journal(journal_code).id
    m = env['account.move'].create(vals)
    m.action_post()
    return m


def pay(move, dt, journal_code, amount=None):
    ctx = dict(active_model='account.move', active_ids=move.ids)
    vals = {'journal_id': journal(journal_code).id, 'payment_date': dt}
    if amount:
        vals['amount'] = amount
    env['account.payment.register'].with_context(**ctx).create(vals)._create_payments()


def misc(dt, name, rows):
    """rows: (mã TK, nợ, có, partner|None)."""
    m = env['account.move'].create({
        'move_type': 'entry', 'journal_id': journal('MISC').id, 'date': dt, 'ref': name,
        'line_ids': [Command.create({'account_id': acc(c).id, 'debit': dr, 'credit': cr, 'name': name,
                                     'partner_id': p.id if p else False}) for c, dr, cr, p in rows],
    })
    m.action_post()
    return m


# --- 1. Góp vốn điều lệ ----------------------------------------------------------------
misc(D(10, 1), 'Góp vốn điều lệ đợt 1', [
    ('112', 400_000_000, 0, None), ('111', 100_000_000, 0, None), ('4111', 0, 500_000_000, None)])

# --- 2. Mua TSCĐ và hàng hóa -----------------------------------------------------------
v10, v8 = tax('purchase', 10), tax('purchase', 8)
b = post_move('in_invoice', s2, D(10, 2), [line('Máy chủ Dell PowerEdge R450', 1, 60_000_000, v10, acc('211'))],
              'HD-PV-0412')
pay(b, D(10, 5), 'BNK1')
b = post_move('in_invoice', s1, D(10, 3), [line('Thiết bị POS bán hàng (30 bộ)', 30, 5_000_000, v10, acc('156'))],
              'HD-TT-2210')
pay(b, D(10, 10), 'BNK1', 82_500_000)  # trả 50%, còn nợ phải trả
# --- 3. Chi phí hoạt động ---------------------------------------------------------------
for m_, d_ in ((10, 1), (11, 1)):
    b = post_move('in_invoice', s3, D(m_, d_), [line('Tiền thuê văn phòng tháng %d/2026' % m_, 1, 25_000_000, v10, acc('6427'))],
                  'HD-PG-%d' % m_)
    pay(b, D(m_, d_ + 4), 'BNK1')
b = post_move('in_invoice', s4, D(10, 31), [line('Tiền điện tháng 10/2026', 1, 8_500_000, v10, acc('6427'))], 'HD-DL-1031')
pay(b, D(11, 6), 'BNK1')
b = post_move('in_invoice', s5, D(10, 15), [line('Văn phòng phẩm, giấy in', 1, 3_200_000, v10, acc('6423'))], 'HD-HH-884')
pay(b, D(10, 15), 'CSH1')
post_move('in_invoice', s6, D(11, 2), [line('Chiến dịch quảng cáo Facebook/Google tháng 11', 1, 20_000_000, v8, acc('6417'))],
          'HD-VQ-3105')  # chưa thanh toán

# --- 4. Bán hàng ------------------------------------------------------------------------
t10, t8, t0 = tax('sale', 10), tax('sale', 8), tax('sale', 0)
sales = [
    (c1, D(10, 8), 'Bản quyền phần mềm quản lý bán hàng (12 tháng)', 1, 120_000_000, t10, ('BNK1', D(10, 20), None)),
    (c2, D(10, 12), 'Triển khai và đào tạo hệ thống', 1, 80_000_000, t10, ('CSH1', D(10, 25), None)),
    (c3, D(10, 15), 'Thiết bị POS bán hàng (10 bộ)', 10, 4_500_000, t8, ('BNK1', D(10, 30), 20_000_000)),
    (c4, D(10, 20), 'Hệ thống quản lý kho cho 3 chi nhánh', 1, 200_000_000, t10, None),
    (c5, D(10, 28), 'Dịch vụ phần mềm xuất khẩu (khách nước ngoài)', 1, 30_000_000, t0, ('BNK1', D(11, 4), None)),
    (c1, D(11, 3), 'Phí bảo trì hệ thống tháng 11', 1, 15_000_000, t10, ('BNK1', D(11, 8), None)),
    (c2, D(11, 5), 'Thiết bị POS bán hàng (8 bộ)', 8, 4_500_000, t8, ('CSH1', D(11, 12), 10_000_000)),
    (c3, D(11, 7), 'Mở rộng module kho (gói nâng cấp)', 1, 150_000_000, t10, None),
    (c5, D(11, 10), 'Dịch vụ triển khai và đào tạo nhân viên', 1, 25_000_000, t10, ('BNK1', D(11, 14), None)),
    (c4, D(11, 12), 'Bản quyền phần mềm CRM (6 tháng)', 1, 60_000_000, t10, None),
]
invs = []
for p_, d_, nm, q, pr, tx, pm in sales:
    inv = post_move('out_invoice', p_, d_, [line(nm, q, pr, tx)])
    invs.append(inv)
    if pm:
        pay(inv, pm[1], pm[0], pm[2])
# Hàng trả lại / giảm giá cho khách An Phát một phần hóa đơn 20/10
post_move('out_refund', c4, D(11, 8), [line('Giảm giá do chậm tiến độ bàn giao', 1, 10_000_000, t10)])

# --- 5. Giá vốn, lương, bảo hiểm, lãi ngân hàng ---------------------------------------
misc(D(10, 31), 'Giá vốn thiết bị POS xuất bán tháng 10', [('632', 100_000_000, 0, None), ('156', 0, 100_000_000, None)])
misc(D(10, 31), 'Lương nhân viên tháng 10/2026', [
    ('6421', 120_000_000, 0, None), ('6411', 40_000_000, 0, None), ('3341', 0, 160_000_000, None)])
misc(D(10, 31), 'Trích bảo hiểm tính vào chi phí tháng 10', [('6421', 21_000_000, 0, None), ('3383', 0, 21_000_000, None)])
misc(D(10, 31), 'Lãi tiền gửi ngân hàng tháng 10', [('112', 1_200_000, 0, None), ('515', 0, 1_200_000, None)])
misc(D(11, 5), 'Chi trả lương tháng 10', [('3341', 160_000_000, 0, None), ('112', 0, 160_000_000, None)])
misc(D(11, 12), 'Nộp bảo hiểm xã hội tháng 10', [('3383', 21_000_000, 0, None), ('112', 0, 21_000_000, None)])

env.cr.commit()
n = env['account.move'].search_count([('state', '=', 'posted')])
print('SEED OK: %d bút toán đã ghi sổ' % n)
