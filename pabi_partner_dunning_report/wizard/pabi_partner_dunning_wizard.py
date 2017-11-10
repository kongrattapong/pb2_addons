# -*- coding: utf-8 -*-
from openerp import api, fields, models

SEARCH_OPTIONS = [
    ('today_dunning_report', 'Today Dunning Report'),
    ('printed_report', 'Printed Report'),
]


class PABIPartnerDunningWizard(models.TransientModel):
    _name = 'pabi.partner.dunning.wizard'

    date_run = fields.Date(
        string='Report Run Date',
        default=lambda self: fields.Date.context_today(self),
        help="Always run as today"
    )
    search_options = fields.Selection(
        selection=SEARCH_OPTIONS,
        string="Search",
        required=True,
        default='today_dunning_report',
    )

    @api.model
    def _get_domain(self):
        Report = self.env['pabi.partner.dunning.report']
        date_run = fields.Date.context_today(self)
        domain = [('reconcile_id', '=', False),
                  ('account_type', '=', 'receivable')]
        if self.search_options == 'today_dunning_report':
            _ids = Report.search([('date_maturity', '<=', date_run)])._ids
            domain.append(('move_line_id', 'in', _ids))
        else:
            date_run = self.date_run
            domain += ['|', ('l1_date', '=', date_run),
                       '|', ('l2_date', '=', date_run),
                       ('l3_date', '=', date_run)]
        return domain

    @api.multi
    def run_report(self):
        self.ensure_one()
        action = self.env.ref('pabi_partner_dunning_report.'
                              'action_pabi_partner_dunning_report')
        result = action.read()[0]
        # Get domain
        domain = self._get_domain()
        result.update({'domain': domain})
        if self.search_options == 'printed_report':
            result.update({'context': {}})
        return result
