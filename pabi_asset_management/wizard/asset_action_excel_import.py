# -*- coding: utf-8 -*-
import base64
import os
import xlrd
from xlrd.sheet import ctype_text
import unicodecsv
from datetime import datetime, timedelta
from openerp import fields, models, api, _
from openerp.exceptions import ValidationError


class AssetActionExcelImport(models.TransientModel):
    _name = 'asset.action.excel.import'

    action_type = fields.Selection(
        [('change_owner', 'Change Asset Owner'),
         ('direct_receive', 'Direct Receive Asset'),
         ('transfer', 'Asset Transfer'),
         ('removal', 'Asset Removal')],
        string='Action Type',
        required=True,
    )
    import_file = fields.Binary(
        string='Import File (*.xls)',
        required=True,
    )

    @api.multi
    def action_import_xls(self):
        self.ensure_one()
        if not self.import_file:
            raise ValidationError(_('Please choose excel file to import!'))
        self.env['pabi.xls'].import_xls(
            'account.asset.changeowner', self.import_file)

    #
    # @api.onchange('period_type')
    # def _onchange_pariod_type(self):
    #     self.calendar_period_id = False
    #     self.calendar_from_period_id = False
    #     self.calendar_to_period_id = False
    #
    # @api.onchange('calendar_from_period_id', 'calendar_to_period_id')
    # def _onchange_calendar_from_to_period_id(self):
    #     if self.calendar_from_period_id and self.calendar_to_period_id:
    #         if self.calendar_from_period_id.date_start > \
    #                 self.calendar_to_period_id.date_start:
    #             self.calendar_from_period_id = False
    #             self.calendar_to_period_id = False
    #             return {'warning': {
    #                 'title': 'Incorrect Periods',
    #                 'message': 'From period is later than to period!',
    #             }}
    #
    # @api.multi
    # def run_report(self):
    #     data = {'parameters': {}}
    #     report_name = self.print_format == 'pdf' and \
    #         'account_tax_report_pdf' or 'account_tax_report_xls'
    #
    #     period_ids = []
    #     if self.period_type == 'specific':
    #         period_ids = [self.calendar_period_id.id]
    #     elif self.period_type == 'range':
    #         domain = [('id', '>=', self.calendar_from_period_id.id),
    #                   ('id', '<=', self.calendar_to_period_id.id)]
    #         period_ids = self.env['account.period'].search(domain).ids
    #
    #     # Params
    #     data['parameters']['period_ids'] = period_ids
    #     data['parameters']['tax_id'] = self.tax_id.id
    #     data['parameters']['doc_type'] = self.tax_id.type_tax_use
    #     # Display Params
    #     company = self.env.user.company_id.partner_id
    #     company_name = company.name or ''
    #     data['parameters']['company_name'] = company.title.name and \
    #         company.title.name + ' ' + company_name or company_name
#     data['parameters']['branch_name'] = data['parameters']['company_name']
    #     data['parameters']['branch_vat'] = company.vat or ''
    #     data['parameters']['branch_taxbranch'] = company.taxbranch or ''
    #     data['parameters']['advance_sequence'] = False
    #     res = {
    #         'type': 'ir.actions.report.xml',
    #         'report_name': report_name,
    #         'datas': data,
    #     }
    #     return res
