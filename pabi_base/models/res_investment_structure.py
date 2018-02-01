# -*- coding: utf-8 -*-
from openerp import fields, models, api
from openerp.addons.pabi_base.models.res_common import ResCommon

CONSTRUCTION_PHASE = {
    '1-design': '1-Design',
    '2-control': '2-Control',
    '3-construct': '3-Construct',
    '4-procure': '4-Procurement',
    '5-other': '5-Others',
}


class InvestAssetCommon(object):
    name = fields.Char(
        string='Name',
    )
    org_id = fields.Many2one(
        'res.org',
        string='Org',
        required=False,
    )
    invest_asset_categ_id = fields.Many2one(
        'res.invest.asset.category',
        string='Investment Asset Category'
    )
    name_common = fields.Char(
        string='Common Name',
    )
    owner_section_id = fields.Many2one(
        'res.section',
        string='Owner Section',
        help="Not related to budgeting, this field hold the "
        "section owner of this asset",
    )
    owner_program_id = fields.Many2one(
        'res.program',
        string='Owner Program',
        help="Not related to budgeting, this field hold the "
        "program group owner of this asset",
    )
    request_user_id = fields.Many2one(
        'res.users',
        string='Requester',
    )
    location = fields.Char(
        string='Asset Location',
    )
    quantity = fields.Float(
        string='Quantity',
    )
    price_unit = fields.Float(
        string='Unit Price',
    )
    price_other = fields.Float(
        string='Other Expenses',
    )
    reason_purchase = fields.Selection(
        [('new', 'New'),
         ('replace', 'Replacement'),
         ('extra', 'Extra')],
        string='Reason',
    )
    reason_purchase_text = fields.Text(
        string='Reason Desc.',
    )
    expect_output = fields.Text(
        string='Output',
    )
    planned_utilization = fields.Char(
        string='Utilization (Hr/Yr)',
    )
    specification_summary = fields.Text(
        string='Summary of Specification',
    )
    amount_plan_total = fields.Float(
        string='Budget Plan Amount',
        help="Planned Amount for this asset, regardless of FY",
    )
    # Compute fields
    owner_division_id = fields.Many2one(
        'res.division',
        related='owner_section_id.division_id',
        string='Owner Division',
        readonly=True,
    )
    costcenter_id = fields.Many2one(
        'res.costcenter',
        string='Costcenter',
        related='owner_section_id.costcenter_id',
        store=True,
        readonly=True,
    )
    price_subtotal = fields.Float(
        string='Gross Price',
        compute='_compute_price',
        store=True,
    )
    price_total = fields.Float(
        string='Net Price',
        compute='_compute_price',
        store=True,
    )

    @api.multi
    @api.depends('price_unit', 'quantity', 'price_other')
    def _compute_price(self):
        for rec in self:
            rec.price_subtotal = rec.price_unit * rec.quantity
            rec.price_total = rec.price_subtotal + rec.price_other

    @api.multi
    def _invest_asset_common_dict(self):
        """ Convert into dict """
        self.ensure_one()
        return {
            'name': self.name,
            'org_id': self.org_id.id,
            'invest_asset_categ_id': self.invest_asset_categ_id.id,
            'name_common': self.name_common,
            'owner_section_id': self.owner_section_id.id,
            'owner_program_id': self.owner_program_id.id,
            'request_user_id': self.request_user_id.id,
            'location': self.location,
            'quantity': self.quantity,
            'price_unit': self.price_unit,
            'price_other': self.price_other,
            'reason_purchase': self.reason_purchase,
            'reason_purchase_text': self.reason_purchase_text,
            'expect_output': self.expect_output,
            'planned_utilization': self.planned_utilization,
            'specification_summary': self.specification_summary,
            'amount_plan_total': self.amount_plan_total,
        }


# Investment - Asset
class ResInvestAsset(ResCommon, InvestAssetCommon, models.Model):
    _name = 'res.invest.asset'
    _description = 'Investment Asset'

    fund_ids = fields.Many2many(
        'res.fund',
        'res_fund_invest_asset_rel',
        'invest_asset_id', 'fund_id',
        string='Funds',
        default=lambda self: self.env.ref('base.fund_nstda'),
    )
    fiscalyear_id = fields.Many2one(
        'account.fiscalyear',
        string='Fiscalyear',
        required=True,
    )


class ResInvestAssetCategory(ResCommon, models.Model):
    _name = 'res.invest.asset.category'
    _description = 'Investment Asset Category'


# Investment - Construction
class ResInvestConstruction(ResCommon, models.Model):
    _name = 'res.invest.construction'
    _description = 'Investment Construction'

    phase_ids = fields.One2many(
        'res.invest.construction.phase',
        'invest_construction_id',
        string='Phases',
    )
    org_id = fields.Many2one(
        'res.org',
        string='Org',
        required=False,
    )
    costcenter_id = fields.Many2one(
        'res.costcenter',
        string='Costcenter',
        required=True,
    )
    fund_ids = fields.Many2many(
        'res.fund',
        'res_fund_invest_construction_rel',
        'invest_construction_id', 'fund_id',
        string='Funds',
        default=lambda self: self.env.ref('base.fund_nstda'),
    )


class ResInvestConstructionPhase(ResCommon, models.Model):
    _name = 'res.invest.construction.phase'
    _description = 'Investment Construction Phase'
    _order = 'sequence, id'

    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    invest_construction_id = fields.Many2one(
        'res.invest.construction',
        string='Investment Construction',
        index=True,
        ondelete='cascade',
    )
    phase = fields.Selection(
        sorted(CONSTRUCTION_PHASE.items()),
        string='Phase',
        required=True,
    )
    fund_ids = fields.Many2many(
        'res.fund',
        related='invest_construction_id.fund_ids',
        string='Funds',
    )
    _sql_constraints = [
        ('phase_uniq', 'unique(invest_construction_id, phase)',
            'Phase must be unique for a construction project!'),
    ]

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "[%s] %s - %s" %
                           (rec.invest_construction_id.code,
                            rec.invest_construction_id.name,
                            CONSTRUCTION_PHASE[rec.phase])))
        return result
