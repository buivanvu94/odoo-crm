"""Bộ máy tính báo cáo tài chính: đọc ``account.move.line`` đã ghi sổ và tính từng chỉ tiêu theo công thức dữ liệu."""
from collections import defaultdict

from odoo import api, models
from odoo.exceptions import AccessError, UserError

from .financial_report_line import parse_formula

TITLES = {
    'b01': ('BÁO CÁO TÌNH HÌNH TÀI CHÍNH', 'B01-DN'),
    'b02': ('BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH', 'B02-DN'),
    'b03d': ('BÁO CÁO LƯU CHUYỂN TIỀN TỆ (Theo phương pháp trực tiếp)', 'B03-DN'),
    'b03i': ('BÁO CÁO LƯU CHUYỂN TIỀN TỆ (Theo phương pháp gián tiếp)', 'B03-DN'),
}
# Định nghĩa DUY NHẤT của "tiền và các khoản tương đương tiền" (B01 mã 110, B03 mã 60/70, dòng tiền).
CASH_EQUIVALENT_PREFIXES = ('12811', '12881')  # tiền gửi có kỳ hạn gốc <= 3 tháng
CASH_ONLY_PREFIXES = ('111', '112', '113')  # 113 gồm cả TK trung gian 1131 của payment
CASH_PREFIXES = CASH_ONLY_PREFIXES + CASH_EQUIVALENT_PREFIXES
# TK treo (suspense) của sổ nhật ký tiền / ngân hàng không phải tiền dù mã nằm trong tiền tố 112 (l10n_vn: 1121):
# mã của chúng được đổi sang tiền tố này nên không khớp bất kỳ tiền tố tài khoản nào, chỉ khớp ``@suspense`` và ``*``.
SUSPENSE_PREFIX = '~'
# Tên gọi dùng trong công thức dữ liệu (đối số hàm), ví dụ ``OD(@cash)``.
MACROS = {'@cash': CASH_PREFIXES, '@cash_equivalent': CASH_EQUIVALENT_PREFIXES, '@suspense': (SUSPENSE_PREFIX,)}
CLOSING_PREFIX = '911'

# hàm -> (nguồn số liệu, cách tính từ (nợ, có) của một tài khoản)
FUNCTION_TABLE = {
    'DB': ('cum', lambda d, c: max(d - c, 0.0)),
    'CB': ('cum', lambda d, c: max(c - d, 0.0)),
    'ND': ('cum', lambda d, c: d - c),
    'NC': ('cum', lambda d, c: c - d),
    'OD': ('opening', lambda d, c: d - c),
    'DM': ('period', lambda d, c: d),
    'CM': ('period', lambda d, c: c),
    'NM': ('period', lambda d, c: c - d),
    'CI': ('flows', lambda d, c: max(c - d, 0.0)),
    'CO': ('flows', lambda d, c: max(d - c, 0.0)),
}


class VnFinancialReport(models.AbstractModel):
    _name = 'vn.financial.report'
    _description = 'Vietnam financial statements engine'

    @api.model
    def build(self, report_type, company, date_from, date_to, compare=None):
        """Một báo cáo; xem ``build_all``."""
        return self.build_all([report_type], company, date_from, date_to, compare)[0]

    @api.model
    def build_all(self, report_types, company, date_from, date_to, compare=None):
        """Danh sách ``{title, form_code, date_text, rows, has_prior, prior_text}`` theo ``report_types``.

        ``compare`` là ``(từ_ngày, đến_ngày)`` kỳ so sánh. Số liệu của mỗi kỳ chỉ tính MỘT lần cho cả bộ.
        """
        if not self.env.user.has_group('account.group_account_manager'):
            raise AccessError(self.env._('Only accounting managers can open the financial statements.'))
        if company not in self.env.user.company_ids:
            raise AccessError(self.env._('You are not allowed to access this company.'))
        engine = self.with_company(company)
        lines = engine.env['vn.financial.report.line'].search([])
        current = engine._evaluate(lines, company, date_from, date_to)
        prior = engine._evaluate(lines, company, *compare) if compare else {}
        return [engine._section(lines, rtype, current, prior, date_from, date_to, compare) for rtype in report_types]

    def _section(self, lines, report_type, current, prior, date_from, date_to, compare):
        title, form_code = TITLES[report_type]
        fmt, has_compare = '%d/%m/%Y', bool(compare)
        rows = []
        for line in lines.filtered(lambda l: l.report_type == report_type):
            has_value = bool(line.code)
            key = (report_type, line.code)
            rows.append({
                'code': line.code or '', 'name': line.name, 'level': line.level, 'bold': line.bold,
                'value': current[key] if has_value else None,
                'prior': prior.get(key) if has_value and has_compare else None,
            })
        if report_type == 'b01':
            date_text = self.env._('At %s', date_to.strftime(fmt))
        else:
            date_text = self.env._('From %(start)s to %(end)s', start=date_from.strftime(fmt), end=date_to.strftime(fmt))
        return {'title': title, 'form_code': form_code, 'date_text': date_text, 'rows': rows,
                'has_prior': has_compare, 'prior_text': (
                    '%s - %s' % (compare[0].strftime(fmt), compare[1].strftime(fmt)) if compare else '')}

    # ------------------------------------------------------------------ dữ liệu nguồn
    def _totals(self, domain):
        """``{account_id: [(nợ, có), ...]}`` theo tiền công ty của các dòng đã ghi sổ thỏa ``domain``.

        TK theo dõi chi tiết đối tượng (131/331/141) có một cặp (nợ, có) cho MỖI đối tượng, để số dư Nợ /
        số dư Có của B01 được xác định theo từng đối tượng (không bù trừ giữa các đối tượng). TK khác có một cặp.
        """
        groups = self.env['account.move.line']._read_group(
            domain, ['account_id', 'partner_id'], ['debit:sum', 'credit:sum'])
        result, merged = defaultdict(list), {}
        for account, _partner, debit, credit in groups:
            if account.vn_partner_required:
                result[account.id].append((debit, credit))
            else:
                total = merged.setdefault(account.id, [0.0, 0.0])
                total[0] += debit
                total[1] += credit
        result.update({aid: [tuple(total)] for aid, total in merged.items()})
        return result

    def _flow_totals(self, domain):
        """Như ``_totals`` nhưng bù trừ trong TỪNG bút toán: mỗi (bút toán, TK) cho một cặp chỉ có một vế.

        Phần thu và phần chi của cùng một TK ở hai bút toán khác nhau không triệt tiêu nhau.
        """
        groups = self.env['account.move.line']._read_group(
            domain, ['move_id', 'account_id'], ['debit:sum', 'credit:sum'])
        result = defaultdict(list)
        for _move, account, debit, credit in groups:
            net = debit - credit
            result[account.id].append((max(net, 0.0), max(-net, 0.0)))
        return result

    def _snapshot(self, company, date_from, date_to):
        Line = self.env['account.move.line']
        base = [('company_id', '=', company.id), ('parent_state', '=', 'posted')]
        cum = self._totals(base + [('date', '<=', date_to)])
        opening = self._totals(base + [('date', '<', date_from)])
        accounts = self.env['account.account'].with_company(company).browse(set(cum) | set(opening))
        suspense = company._vn_suspense_accounts().ids
        codes = {account.id: (SUSPENSE_PREFIX if account.id in suspense else '') + (account.vn_display_code or '')
                 for account in accounts}
        # Bút toán kết chuyển (có dòng TK 911) bị loại khỏi phát sinh để báo cáo đúng cả trước và sau khi kết chuyển.
        period = base + [('date', '>=', date_from), ('date', '<=', date_to)]
        closing_accounts = [aid for aid, code in codes.items() if code.startswith(CLOSING_PREFIX)]
        if closing_accounts:
            closing_moves = Line._read_group(period + [('account_id', 'in', closing_accounts)], ['move_id'])
            if closing_moves:
                period.append(('move_id', 'not in', [move.id for (move,) in closing_moves]))
        # Dòng tiền: các dòng không phải tiền của những bút toán có động tiền trong kỳ (trực tiếp theo TK đối ứng).
        cash_ids = [aid for aid, code in codes.items() if code.startswith(CASH_PREFIXES)]
        flows = {}
        if cash_ids:
            cash_moves = Line._read_group(period + [('account_id', 'in', cash_ids)], ['move_id'])
            flows = self._flow_totals(base + [
                ('move_id', 'in', [move.id for (move,) in cash_moves]), ('account_id', 'not in', cash_ids)])
        return {'cum': cum, 'opening': opening, 'period': self._totals(period), 'flows': flows}, codes

    # ------------------------------------------------------------------ tính chỉ tiêu
    @staticmethod
    def _match(codes, arg):
        includes, excludes = [], []
        for token in (part.strip() for part in arg.split(',') if part.strip()):
            target = excludes if token.startswith('!') else includes
            name = token.lstrip('!')
            target.extend(MACROS.get(name, (name,)))
        return [
            aid for aid, code in codes.items()
            if ('*' in includes or code.startswith(tuple(includes))) and not code.startswith(tuple(excludes))]

    def _evaluate(self, lines, company, date_from, date_to):
        """``{(loại_báo_cáo, mã_số): giá_trị}`` cho mọi chỉ tiêu có mã số, đã làm tròn theo tiền tệ công ty."""
        snapshot, codes = self._snapshot(company, date_from, date_to)
        by_key = {(line.report_type, line.code): line for line in lines if line.code}
        matches, values = {}, {}

        def term_value(fn, arg):
            source, pick = FUNCTION_TABLE[fn]
            if arg not in matches:
                matches[arg] = self._match(codes, arg)
            return sum(pick(debit, credit) for aid in matches[arg] for debit, credit in snapshot[source].get(aid, ()))

        def value(key, path=()):
            if key in values:
                return values[key]
            if key not in by_key or key in path:
                raise UserError(self.env._('Financial report formula refers to an unknown or circular line: %s', key))
            line, total = by_key[key], 0.0
            for sign, fn, arg, ref in parse_formula(line.formula):
                if fn:
                    amount = term_value(fn, arg)
                else:
                    target = tuple(ref.split(':')) if ':' in ref else (line.report_type, ref)
                    amount = value(target, path + (key,))
                total += -amount if sign == '-' else amount
            values[key] = company.currency_id.round(total)
            return values[key]

        for key in by_key:
            value(key)
        return values
