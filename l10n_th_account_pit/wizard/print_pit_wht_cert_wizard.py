# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class PrintPITWhtCertWizard(models.TransientModel):
    _name = 'print.pit.wht.cert.wizard'

    company_partner_id = fields.Many2one(
        'res.partner',
        string='Company',
        readonly=True,
    )
    supplier_partner_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        readonly=True,
    )
    company_taxid = fields.Char(
        related='company_partner_id.vat',
        string='Company Tax ID',
        readonly=True,
        size=20,
    )
    supplier_taxid = fields.Char(
        related='supplier_partner_id.vat',
        string='Supplier Tax ID',
        readonly=True,
        size=20,
    )
    supplier_address = fields.Char(
        string='Supplier Address',
        compute='_compute_address',
        readonly=True,
    )
    company_address = fields.Char(
        string='Company Address',
        compute='_compute_address',
        readonly=True,
    )
    wht_line = fields.One2many(
        'pit.wht.cert.tax.line',
        'wizard_id',
        string='Withholding Line',
    )
    calendaryear_id = fields.Many2one(
        'account.fiscalyear.calendar',
        string='Calendar Year',
        required=True,
    )

    @api.multi
    @api.depends('company_partner_id', 'supplier_partner_id')
    def _compute_address(self):
        for rec in self:
            rec.company_address = \
                self._prepare_address(rec.company_partner_id)
            rec.supplier_address = \
                self._prepare_address(rec.supplier_partner_id)

    @api.model
    def default_get(self, fields):
        res = super(PrintPITWhtCertWizard, self).default_get(fields)
        active_id = self._context.get('active_id')
        company_partner = self.env.user.company_id.partner_id
        supplier = self.env['res.partner'].browse(active_id)
        res['company_partner_id'] = company_partner.id
        res['supplier_partner_id'] = supplier.id
        return res

    @api.onchange('calendaryear_id')
    def _onchange_calendaryear_id(self):
        self.wht_line = []
        if not self.calendaryear_id:
            return
        WHTLine = self.env['pit.wht.cert.tax.line']
        pit_lines = self.supplier_partner_id.pit_line.filtered(
            lambda l: l.calendar_year == self.calendaryear_id.calendar_name)
        for line in pit_lines.filtered(lambda l:
                                       l.voucher_id.state == 'posted'): #line == personal_income_type
            wht_line = WHTLine.new()
            wht_line.voucher_id = line.voucher_id
            wht_line.date = line.date
            wht_line.base = line.amount_income
            wht_line.amount = -line.amount_wht
            wht_line.income_type = line.wht_cert_income_type
            self.wht_line += wht_line

    @api.multi
    def run_report(self):
        data = {'parameters': {}}
        form_data = self._get_form_data()
        data['parameters'] = form_data
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': 'report_pit_withholding_cert',
            'datas': data,
            'context': {'lang': 'th_TH'},
        }
        return res

    @api.model
    def _get_form_data(self):
        """ Data to pass as parameter in iReport """
        data = {}
        TH = {'lang': 'th_TH'}
        company = self.env.user.company_id.partner_id
        supplier = self.supplier_partner_id
        if not company.vat or not supplier.vat:
            raise ValidationError(_('No Tax ID on Company or Supplier'))
        data['company_name'] = company.display_name2
        data['supplier_name'] = supplier.display_name2
        company_taxid = len(company.vat) == 13 and company.vat or ''
        data['company_taxid'] = list(company_taxid)
        supplier_taxid = len(supplier.vat) == 13 and supplier.vat or ''
        data['supplier_taxid'] = list(supplier_taxid)
        data['company_address'] = self.company_address
        data['supplier_address'] = self.supplier_address
        data['buddha_year'] = int(self.calendaryear_id.calendar_name) + 543
        data['type1_tax'] = self._get_summary_by_type('tax','1')
        data['type2_tax'] = self._get_summary_by_type('tax','2')
        data['type1_base'] = self._get_summary_by_type('base','1')
        data['type2_base'] = self._get_summary_by_type('base','2')
        data['total_base'] = self._get_summary_by_type('base')
        data['total_tax'] = self._get_summary_by_type('tax')
        data['signature'] = self.with_context(TH).env.user.display_name2
        if self.with_context(TH).env.user.partner_id.sign_image  == None:
            data['sign_image'] = ""
        else:
            data['sign_image'] = self.with_context(TH).env.user.partner_id.sign_image 
#         data['sign_image'] =   supplier.sign_image
        return data

    @api.model
    def _get_summary_by_type(self, column, ttype='all'):
        wht_lines = self.wht_line
        if ttype != 'all':
            wht_lines = wht_lines.filtered(lambda l:
                                           l.income_type == ttype)
        if column == 'base':
            return abs(sum(wht_lines.filtered(
                lambda l: l.voucher_id.state == 'posted').mapped('base')))
        if column == 'tax':
            return abs(sum(wht_lines.filtered(
                lambda l: l.voucher_id.state == 'posted').mapped('amount')))
    
  
            
    @api.model
    def _prepare_address(self, partner):
        address_list = [partner.street, partner.street2, partner.city,
                        partner.township_id.name, partner.district_id.name,
                        partner.province_id.name, partner.zip, ]
        address_list = filter(lambda x: x is not False and x != '',
                              address_list)
        return ' '.join(address_list).strip()


class PITWhtCertTaxLine(models.TransientModel):
    _name = 'pit.wht.cert.tax.line'

    wizard_id = fields.Many2one(
        'print.pit.wht.cert.wizard',
        string='Wizard',
        index=True,
    )
    voucher_id = fields.Many2one(
        'account.voucher',
        string='Voucher',
        readonly=True,
    )
    date = fields.Date(
        string='Date',
        readonly=True,
    )
    base = fields.Float(
        string='Base Amount',
        readonly=True,
    )
    amount = fields.Float(
        string='Tax Amount',
        readonly=True,
    )
    income_type = fields.Char(
        string='Income Type',
        readonly=True,
    )
