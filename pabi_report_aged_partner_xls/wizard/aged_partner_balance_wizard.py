# -*- coding: utf-8 -*-
###############################################################################
#
#   report_aged_partner_xls for Odoo
#   Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from openerp.osv import orm


class aged_partner_balance_webkit_wizard(orm.TransientModel):
    _inherit = 'account.aged.trial.balance.webkit'

    def xls_export(self, cr, uid, ids, context=None):
        return self.check_report(cr, uid, ids, context=context)

    def _print_report(self, cr, uid, ids, data, context=None):
        context = context or {}
        if context.get('xls_export'):
            data['form'].update(
                self.read(cr, uid, ids, ['period_length'], context=context)[0])
            data = self.pre_print_report(cr, uid, ids, data, context=context)
            return {
                'type': 'ir.actions.report.xml',
                'report_name':
                'account.account_report_aged_partner_balance_xls',
                'datas': data
            }
        else:
            return super(aged_partner_balance_webkit_wizard, self).\
                _print_report(cr, uid, ids, data, context=context)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
