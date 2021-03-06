# -*- coding: utf-8 -*-
from openerp import models, api


class BudgetPolicy(models.Model):
    _inherit = 'budget.policy'

    @api.model
    def _get_planned_expense_hook(self, policy, plans):
        """ We have this hook as with internal charge change it """
        if policy.fiscalyear_id.control_ext_charge_only and \
                'planned_expense_external' in plans._fields.keys():
            return sum(plans.mapped('planned_expense_external'))
        else:
            return super(BudgetPolicy, self)._get_planned_expense_hook(plans)
