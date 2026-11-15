"""Nâng cấp lên 20.0.1.1.0: bổ sung tài khoản đối ứng còn thiếu cho bút toán đã ghi sổ."""
from odoo import SUPERUSER_ID, api

from odoo.addons.company_accounting_vn.hooks import backfill_counterparts


def migrate(cr, version):
    backfill_counterparts(api.Environment(cr, SUPERUSER_ID, {}))
