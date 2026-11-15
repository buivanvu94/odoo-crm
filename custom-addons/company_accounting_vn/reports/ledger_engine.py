"""Tính dữ liệu các sổ kế toán từ account.move.line đã ghi sổ (parent_state = 'posted').

Số dư đầu kỳ và bảng cân đối dùng ``_read_group`` (một truy vấn tổng hợp, tôn trọng quyền và
quy tắc đa công ty); chỉ dòng phát sinh trong kỳ mới được đọc chi tiết bằng một ``search_fetch``.
Bộ lọc (domain) nằm ở ledger_domains.py. Mọi dòng kết quả là dict có khóa trùng tên field của ``accounting.report.line``.
"""
from odoo import _, api, models
from odoo.exceptions import UserError

from .ledger_layout import BOOK_PREFIX, COLUMNS, FORM_CODES, TITLES

LINE_FIELDS = ['date', 'move_name', 'move_id', 'name', 'account_id', 'partner_id', 'journal_id',
               'debit', 'credit', 'counterpart_name']


def _sides(net):
    """Tách số dư thuần (Nợ - Có) thành cặp (dư Nợ, dư Có)."""
    return (net, 0.0) if net >= 0 else (0.0, -net)


class VNLedgerEngine(models.AbstractModel):
    _name = 'vn.ledger.engine'
    _description = 'Vietnamese ledger computation engine'

    @api.model
    def build(self, wizard):
        """Trả về {'title', 'form_code', 'columns', 'rows', 'period'} cho wizard.

        Mã tài khoản phụ thuộc công ty, nên toàn bộ phép tính chạy trong ngữ cảnh công ty của wizard
        (không phải công ty đang hoạt động của người dùng).
        """
        wizard.ensure_one()
        wizard = wizard.with_company(wizard.company_id)
        return self.with_company(wizard.company_id)._build(wizard)

    @api.model
    def _build(self, wizard):
        kind = wizard.report_type
        domain = self._base_domain(wizard)
        if kind == 'journal':
            rows = self._journal_rows(wizard, domain)
        elif kind == 'ledger':
            rows = self._sectioned_rows(wizard, domain + self._account_domain(wizard), 'account_id')
        elif kind in ('cash', 'bank'):
            rows = self._sectioned_rows(wizard, domain + self._cash_bank_domain(wizard, kind), 'journal_id')
        elif kind in ('partner_131', 'partner_331'):
            accounts = self._accounts_by_prefix(wizard.company_id, [BOOK_PREFIX[kind]])
            rows = self._sectioned_rows(wizard, domain + [('account_id', 'in', accounts.ids)], 'partner_id')
        elif kind == 'trial':
            rows = self._trial_rows(wizard, domain + self._account_domain(wizard))
        else:
            raise UserError(_('Unknown report type %s', kind))
        return {
            'title': TITLES[kind], 'form_code': FORM_CODES[kind], 'columns': COLUMNS[kind], 'rows': rows,
            'period': 'Từ ngày %s đến ngày %s' % (
                wizard.date_from.strftime('%d/%m/%Y'), wizard.date_to.strftime('%d/%m/%Y')),
        }

    # ------------------------------------------------------------------ row builders

    @api.model
    def _line_row(self, line, codes):
        return {
            'kind': 'line', 'date': line.date.strftime('%d/%m/%Y'),
            'voucher': line.move_name or line.move_id.name or '', 'label': line.name or '',
            'account': codes[line.account_id.id], 'counterpart': line.counterpart_name or '',
            'partner': line.partner_id.display_name or '', 'journal': line.journal_id.code or '',
            'debit': line.debit, 'credit': line.credit,
        }

    @api.model
    def _fetch_lines(self, wizard, domain):
        lines = self.env['account.move.line'].search_fetch(
            domain + [('date', '>=', wizard.date_from), ('date', '<=', wizard.date_to)],
            LINE_FIELDS, order='date, move_name, id')
        codes = {a.id: a.vn_display_code for a in lines.account_id}
        return lines, codes

    @api.model
    def _grand_total(self, rows):
        lines = [r for r in rows if r['kind'] == 'line']
        return {'kind': 'grand', 'label': 'Tổng cộng',
                'debit': sum(r['debit'] for r in lines), 'credit': sum(r['credit'] for r in lines)}

    @api.model
    def _journal_rows(self, wizard, domain):
        lines, codes = self._fetch_lines(wizard, domain + self._account_domain(wizard))
        rows = [self._line_row(line, codes) for line in lines]
        return rows + [self._grand_total(rows)]

    @api.model
    def _group_label(self, record, field):
        if field == 'account_id':
            return '%s - %s' % (record.vn_display_code, record.name)
        if field == 'partner_id':
            return record.display_name if record else 'Không có đối tượng'
        return record.display_name

    @api.model
    def _sectioned_rows(self, wizard, domain, field):
        """Mỗi nhóm (TK / sổ nhật ký / đối tượng): đầu kỳ, các dòng với số dư lũy kế, cộng và cuối kỳ."""
        opening = {rec.id: debit - credit for rec, debit, credit in self.env['account.move.line']._read_group(
            domain + [('date', '<', wizard.date_from)], [field], ['debit:sum', 'credit:sum'])}
        lines, codes = self._fetch_lines(wizard, domain)
        by_group = {}
        for line in lines:
            by_group.setdefault(line[field].id, []).append(line)
        model = self.env['account.move.line']._fields[field].comodel_name
        records = {rec.id: rec for rec in self.env[model].browse([i for i in set(opening) | set(by_group) if i])}
        records[False] = self.env[model]
        groups = [gid for gid in set(opening) | set(by_group) if by_group.get(gid) or round(opening.get(gid, 0), 6)]
        groups.sort(key=lambda gid: self._group_label(records[gid], field))
        rows = []
        for gid in groups:
            balance = opening.get(gid, 0.0)
            rows.append({'kind': 'group', 'label': self._group_label(records[gid], field)})
            rows.append(dict(kind='open', label='Số dư đầu kỳ', **self._bal(balance)))
            section = []
            for line in by_group.get(gid, []):
                balance += line.debit - line.credit
                row = self._line_row(line, codes)
                row.update(self._bal(balance))
                section.append(row)
            rows += section
            rows.append({'kind': 'total', 'label': 'Cộng phát sinh trong kỳ',
                         'debit': sum(r['debit'] for r in section), 'credit': sum(r['credit'] for r in section)})
            rows.append(dict(kind='close', label='Số dư cuối kỳ', **self._bal(balance)))
        return rows + [self._grand_total(rows)]

    @api.model
    def _bal(self, net):
        debit, credit = _sides(net)
        return {'bal_debit': debit, 'bal_credit': credit}

    @api.model
    def _trial_rows(self, wizard, domain):
        """Bảng cân đối số phát sinh: mỗi TK cấp 1 là một dòng tổng, kèm các TK con (mã > 3 ký tự)."""
        aml = self.env['account.move.line']
        figures = {}  # account -> [net đầu kỳ, nợ, có]
        for account, debit, credit in aml._read_group(
                domain + [('date', '<', wizard.date_from)], ['account_id'], ['debit:sum', 'credit:sum']):
            figures.setdefault(account, [0.0, 0.0, 0.0])[0] = debit - credit
        for account, debit, credit in aml._read_group(
                domain + [('date', '>=', wizard.date_from), ('date', '<=', wizard.date_to)],
                ['account_id'], ['debit:sum', 'credit:sum']):
            figures.setdefault(account, [0.0, 0.0, 0.0])[1:] = [debit, credit]
        parents = {}
        for account, fig in figures.items():
            if any(round(v, 6) for v in fig):
                parents.setdefault(account.vn_display_code[:3], []).append((account, fig))
        rows = []
        for code in sorted(parents):
            members = sorted(parents[code], key=lambda m: m[0].code)
            total = [sum(fig[i] for _acc, fig in members) for i in range(3)]
            names = {acc.vn_display_code: acc.name for acc, _fig in members}
            rows.append(self._trial_row('group', code, names.get(code) or members[0][0].name, total))
            rows += [self._trial_row('line', acc.vn_display_code, acc.name, fig)
                     for acc, fig in members if len(acc.vn_display_code) > 3]
        groups = [r for r in rows if r['kind'] == 'group']
        keys = ('open_debit', 'open_credit', 'debit', 'credit', 'close_debit', 'close_credit')
        return rows + [dict({k: sum(r[k] for r in groups) for k in keys}, kind='grand', account='', label='Tổng cộng')]

    @api.model
    def _trial_row(self, kind, code, name, fig):
        net_open, debit, credit = fig
        open_debit, open_credit = _sides(net_open)
        close_debit, close_credit = _sides(net_open + debit - credit)
        return {'kind': kind, 'account': code, 'label': name, 'open_debit': open_debit, 'open_credit': open_credit,
               'debit': debit, 'credit': credit, 'close_debit': close_debit, 'close_credit': close_credit}
