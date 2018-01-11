# -*- coding: utf-8 -*-
from openerp import tools
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from .budget_plan_common import BPCommon, BPLMonthCommon
from openerp.addons.account_budget_activity.models.account_activity \
    import ActivityCommon
# from openerp.addons.document_status_history.models.document_history import \
#     LogCommon


class BudgetPlanProject(BPCommon, models.Model):
    _name = 'budget.plan.project'
    _inherit = ['mail.thread']
    _description = "Project - Budget Plan"
    _order = 'id desc'

    # COMMON
    plan_line_ids = fields.One2many(
        'budget.plan.project.line',
        'plan_id',
        string='Budget Plan Lines',
        copy=True,
        track_visibility='onchange',
    )
    plan_revenue_line_ids = fields.One2many(
        'budget.plan.project.line',
        'plan_id',
        string='Revenue Plan Lines',
        copy=True,
        domain=[('budget_method', '=', 'revenue')],  # Have domain
        track_visibility='onchange',
    )
    plan_expense_line_ids = fields.One2many(
        'budget.plan.project.line',
        'plan_id',
        string='Expense Plan Lines',
        copy=True,
        domain=[('budget_method', '=', 'expense')],  # Have domain
        track_visibility='onchange',
    )
    # Select Dimension - Project
    program_id = fields.Many2one(
        'res.program',
        string='Program',
        required=True,
    )
    program_group_id = fields.Many2one(
        'res.program.group',
        string='Program Group',
        related='program_id.program_group_id',
        readonly=True,
        store=True,
    )
    functional_area_id = fields.Many2one(
        'res.functional.area',
        string='Functional Area',
        related='program_id.functional_area_id',
        readonly=True,
        store=True,
    )
    _sql_constraints = [
        ('uniq_plan', 'unique(program_id, fiscalyear_id)',
         'Duplicated budget plan for the same program is not allowed!'),
    ]

    @api.model
    def create(self, vals):
        name = self._get_doc_number(vals['fiscalyear_id'],
                                    'res.program', vals['program_id'])
        vals.update({'name': name})
        return super(BudgetPlanProject, self).create(vals)

    @api.model
    def generate_plans(self, fiscalyear_id=None):
        if not fiscalyear_id:
            raise ValidationError(_('No fiscal year provided!'))
        # Find existing plans, and exclude them
        plans = self.search([('fiscalyear_id', '=', fiscalyear_id)])
        _ids = plans.mapped('program_id')._ids
        # Find Programs
        programs = self.env['res.program'].search([('id', 'not in', _ids),
                                                   ('special', '=', False)])
        plan_ids = []
        for program in programs:
            plan = self.create({'fiscalyear_id': fiscalyear_id,
                                'program_id': program.id,
                                'user_id': False})
            plan_ids.append(plan.id)

        # Special for Project Based, also create budget control too
        self.env['account.budget'].\
            generate_project_base_controls(fiscalyear_id)

        return plan_ids

    @api.multi
    def convert_to_budget_control(self):
        """ Create a budget control from budget plan """
        self.ensure_one()
        head_src_model = self.env['budget.plan.project']
        line_src_model = self.env['budget.plan.project.line']
        budget = self._convert_plan_to_budget_control(self.id,
                                                      head_src_model,
                                                      line_src_model)
        return budget

    @api.multi
    def prepare_prev_fy_commitment(self):
        """ Prepre commitment amount from previous year from PO/EX """
        Fiscal = self.env['account.fiscalyear']
        Commit = self.env['budget.plan.project.commit.view']
        self.mapped('plan_line_ids').unlink()
        for plan in self:
            prev_fy = Fiscal.search(
                [('date_stop', '<', plan.fiscalyear_id.date_start)],
                order='date_stop desc', limit=1)
            if not prev_fy:
                return
            commits = Commit.search([
                ('program_id', '=', plan.program_id.id),
                ('fiscalyear_id', '=', prev_fy.id)])
            plan_lines = []
            for commit in commits:
                val = {'c_or_n': 'continue',
                       'project_id': commit.project_id.id,
                       'name': commit.project_id.name,
                       'fund_id': commit.fund_id.id,
                       'amount_plan': commit.planned,
                       'amount_released': commit.released,
                       'total_commitment': commit.all_commit,
                       'actual_amount': commit.actual,
                       'budget_remaining': commit.remain,
                       'estimated_commitment': 0.0,  # ???
                       'm0': 0.0,  # ???
                       # MORE FIELDS, Still don't know how to get it from
                       }
                plan_lines.append((0, 0, val))
            plan.write({'plan_line_ids': plan_lines})


class BudgetPlanProjectLine(BPLMonthCommon, ActivityCommon, models.Model):
    _name = 'budget.plan.project.line'
    _description = "Project - Budget Plan Line"

    # COMMON
    chart_view = fields.Selection(
        default='project_base',  # Project
    )
    plan_id = fields.Many2one(
        'budget.plan.project',
        string='Budget Plan',
        ondelete='cascade',
        index=True,
        required=True,
    )
    # Extra
    name = fields.Char(
        string='Project Name',
    )
    program_id = fields.Many2one(
        related='plan_id.program_id',
        store=True,
        readonly=True,
    )
    activity_group_id = fields.Many2one(
        'account.activity.group',
        string='Activity Group',
        required=False,  # Change from BPLCommon to required=False
    )
    activity_id = fields.Many2one(
        'account.activity',
        string='Activity',
    )
    # Project Based Specific
    c_or_n = fields.Selection(
        [('continue', 'Continue'),
         ('new', 'New')],
        string='C/N',
        default='new',
    )
    # Budget Control
    amount_plan = fields.Float(  # cur_current_budget
        string='Current Budget',
        readonly=True,
        help="This FY Budget Plan (what is different with budget released?)",
    )
    amount_released = fields.Float(  # cur_release_budget
        string='Released Budget',
        readonly=True,
        help="This FY Budget Released",
    )
    total_commitment = fields.Float(  # cur_commit_budget
        string='Current Total Commit',
        readonly=True,
        help="This FY Total Commitment",
    )
    actual_amount = fields.Float(  # cur_actual
        string='Current Actual',
        readonly=True,
        help="This FY actual amount",
    )
    budget_remaining = fields.Float(  # cur_remaining_budget
        string='Remaining Budget',
        help="This FY Budget Remaining"
    )
    estimated_commitment = fields.Float(  # cur_estimated_commitment
        string='Estimated Commitment',
        help="??? What is this ???"
    )
    fy1 = fields.Float(
        string='FY1',
    )
    fy2 = fields.Float(
        string='FY2',
    )
    fy3 = fields.Float(
        string='FY3',
    )
    fy4 = fields.Float(
        string='FY4',
    )
    fy5 = fields.Float(
        string='FY5',
    )
    total = fields.Float(
        string='Total',
    )
    # Project Detail
    project_kind = fields.Selection(
        [('research', 'Research'),
         ('non_research', 'Non-Research')],
        string='Research / Non-Research',
    )
    project_objective = fields.Char(
        string='Objective',
    )
    project_type = fields.Char(
        string='Project Type',
    )
    manager_employee_id = fields.Many2one(
        'hr.employee',
        string='Project Manager',
    )
    date_from = fields.Date(
        string='Start Date',
    )
    date_to = fields.Date(
        string='End Date',
    )
    project_duration = fields.Integer(
        string='Duration',
    )
    project_status = fields.Char(
        string='Project Status',
    )
    analyst_employee_id = fields.Many2one(
        'hr.employee',
        string='Project Analyst',
    )
    ref_program_id = fields.Many2one(
        'res.program',
        string='Program Reference',
    )
    external_fund_type = fields.Selection(
        [('government', 'Government'),
         ('private', 'Private Organization'),
         ('oversea', 'Oversea')],
        string='External Fund Type',
    )
    external_fund_name = fields.Char(
        string='External Fund Name',
    )
    priority = fields.Char(
        string='Priority',
    )
    # Project Performance (myPerformance)
    pfm_publications = fields.Integer(
        string='Publication',
    )
    pfm_patents = fields.Integer(
        string='Patent',
    )
    pfm_petty_patents = fields.Integer(
        string='Petty Patent',
    )
    pfm_copyrights = fields.Integer(
        string='Copy Right',
    )
    pfm_trademarks = fields.Integer(
        string='Trademark',
    )
    pfm_plant_varieties = fields.Integer(
        string='Plant Varieties',
    )
    pfm_laboratory_prototypes = fields.Integer(
        string='Laboratory Prototype',
    )
    pfm_field_prototypes = fields.Integer(
        string='Field Prototype',
    )
    pfm_commercial_prototypes = fields.Integer(
        string='Commercial Prototype',
    )
    pfm_revenue_budget = fields.Float(
        string='Revenue Budget',
    )
    pfm_revenue_overall_plan = fields.Float(
        string='Overall Revenue Plan',
    )
    pfm_revenue_accum = fields.Float(
        string='Accum. Revenue',
    )
    pfm_revenue_current_year = fields.Float(
        string='Current Year Revenue',
    )
    pfm_expense_overall_budget = fields.Float(
        string='Overall Expense Budget',
    )
    pfm_expense_accum = fields.Float(
        string='Accum. Expense',
    )
    pfm_commitment_accum = fields.Float(
        string='Accum. Commitment',
    )
    pfm_expense_remaining_budget = fields.Float(
        string='Remaining Expense Budget',
    )

    # Required for updating dimension
    # FIND ONLY WHAT IS NEED AND USE related field.

    @api.multi
    def edit_project(self):
        self.ensure_one()
        action = self.env.ref('pabi_budget_plan.'
                              'action_budget_plan_project_line_view')
        result = action.read()[0]
        view = self.env.ref('pabi_budget_plan.'
                            'view_budget_plan_project_line_form')
        result.update(
            {'res_id': self.id,
             'view_id': False,
             'view_mode': 'form',
             'views': [(view.id, 'form')],
             'context': False, })
        return result


class BudgetPlanProjectCommitView(models.Model):
    _name = 'budget.plan.project.commit.view'
    _auto = False
    _description = 'FY budget commitment for project base'

    fiscalyear_id = fields.Many2one(
        'account.fiscalyear',
        string='Fiscalyear',
        readonly=True,
    )
    fund_id = fields.Many2one(
        'res.fund',
        string='Fund',
        readonly=True,
    )
    program_id = fields.Many2one(
        'res.program',
        string='Program',
        readonly=True,
    )
    project_id = fields.Many2one(
        'res.project',
        string='Project',
        readonly=True,
    )
    planned = fields.Float(
        string='Planned',
        readonly=True,
    )
    released = fields.Float(
        string='Released',
        readonly=True,
    )
    so_commit = fields.Float(
        string='SO Commit',
        readonly=True,
    )
    pr_commit = fields.Float(
        string='PR Commit',
        readonly=True,
    )
    po_commit = fields.Float(
        string='PO Commit',
        readonly=True,
    )
    exp_commit = fields.Float(
        string='EX Commit',
        readonly=True,
    )
    all_commit = fields.Float(
        string='All Commit',
        readonly=True,
    )
    actual = fields.Float(
        string='Actual',
        readonly=True,
    )
    consumed = fields.Float(
        string='Consumed',
        readonly=True,
    )
    remain = fields.Float(
        string='Ramining',
        readonly=True,
    )

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""create or replace view %s as (
            select max(id) id, project_id, fiscalyear_id, program_id, fund_id,
                sum(planned_amount) as planned,
                sum(released_amount) as released,
                -sum(amount_so_commit) so_commit,
                -sum(amount_pr_commit) pr_commit,
                -sum(amount_po_commit) po_commit,
                -sum(amount_exp_commit) exp_commit,
                -sum(amount_so_commit + amount_pr_commit +
                     amount_po_commit + amount_exp_commit) all_commit,
                -sum(amount_actual) actual,
                -sum(amount_consumed) consumed,
                sum(amount_balance) remain,
                sum(released_amount + amount_actual) carry_forward
            from budget_monitor_report
            where chart_view = 'project_base'
            group by project_id, fiscalyear_id, program_id, fund_id
        )""" % self._table)
