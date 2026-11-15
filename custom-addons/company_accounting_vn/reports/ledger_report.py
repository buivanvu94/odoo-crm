"""Dữ liệu cho mẫu in QWeb của sổ kế toán (action ``action_report_vn_ledger``)."""
from odoo import api, models


class ReportVNLedger(models.AbstractModel):
    _name = 'report.company_accounting_vn.report_vn_ledger'
    _description = 'Vietnamese ledger QWeb report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizards = self.env['accounting.report.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'accounting.report.wizard',
            'docs': wizards,
            'reports': {wizard.id: wizard._get_report_data() for wizard in wizards},
        }
