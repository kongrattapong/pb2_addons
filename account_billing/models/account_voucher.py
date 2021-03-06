# -*- coding: utf-8 -*-
from openerp import fields, models, api


class AccountVoucher(models.Model):

    _inherit = "account.voucher"

    billing_id = fields.Many2one(
        'account.billing',
        string='Billing Ref',
        domain=[('state', '=', 'billed'), ('payment_id', '=', False)],
        readonly=True,
        states={'draft': [('readonly', False)]})

    @api.multi
    def proforma_voucher(self):
        for rec in self:
            # Write payment id back to Billing Document
            if rec.billing_id:
                rec.billing_id.write({'payment_id': rec.id,
                                      'state': 'billed'})
        return super(AccountVoucher, self).proforma_voucher()

    @api.multi
    def cancel_voucher(self):
        for rec in self:
            # Set payment_id in Billing back to False
            if rec.billing_id:
                rec.billing_id.payment_id = False
        return super(AccountVoucher, self).cancel_voucher()

    def onchange_billing_id(self, cr, uid, ids, partner_id, journal_id,
                            amount, currency_id, ttype, date, context=None):
        if not partner_id or not journal_id:
            return {}
        res = self.recompute_voucher_lines(cr, uid, ids, partner_id,
                                           journal_id, amount, currency_id,
                                           ttype, date, context=context)
        vals = self.recompute_payment_rate(cr, uid, ids, res, currency_id,
                                           date, ttype, journal_id,
                                           amount)
        for key in vals.keys():
            res[key].update(vals[key])
        if ttype == 'sale':
            del(res['value']['line_dr_ids'])
            del(res['value']['pre_line'])
            del(res['value']['payment_rate'])
        elif ttype == 'purchase':
            del(res['value']['line_cr_ids'])
            del(res['value']['pre_line'])
            del(res['value']['payment_rate'])
        if context.get('billing_id', False):
            bill_obj = self.pool.get('account.billing')
            billing = bill_obj.browse(cr, uid, context.get('billing_id'))
            res['value'].update({'amount': billing.billing_amount})
        return res

    def finalize_voucher_move_lines(self, cr, uid, ids, account_move_lines,
                                    partner_id, journal_id, price,
                                    currency_id, ttype, date, context=None):

        super(AccountVoucher, self).finalize_voucher_move_lines(
            cr, uid, ids, account_move_lines,
            partner_id, journal_id, price,
            currency_id, ttype, date, context=None)

        if context is None:
            context = {}

        # Rewrite code from get account type.
        account_type = None
        if context.get('account_id'):
            account_type = self.pool['account.account'].browse(
                cr, uid,
                context['account_id'],
                context=context).type
        if ttype == 'payment':
            if not account_type:
                account_type = 'payable'
        else:
            if not account_type:
                account_type = 'receivable'

        move_line_pool = self.pool.get('account.move.line')
        if not context.get('move_line_ids', False):
            billing_id = context.get('billing_id', False)
            if billing_id > 0:
                billing_obj = self.pool.get('account.billing')
                billing = billing_obj.browse(cr, uid,
                                             billing_id, context=context)
                ids = move_line_pool.search(
                    cr, uid, [
                        ('state', '=', 'valid'),
                        ('account_id.type', '=', account_type),
                        ('reconcile_id', '=', False),
                        ('partner_id', '=', partner_id),
                        ('id', 'in', [
                            line.reconcile and
                            line.move_line_id.id or
                            False
                            for line in billing.line_cr_ids])
                    ], context=context)
            else:  # -- ecosoft
                ids = move_line_pool.search(
                    cr, uid, [
                        ('state', '=', 'valid'),
                        ('account_id.type', '=', account_type),
                        ('reconcile_id', '=', False),
                        ('partner_id', '=', partner_id)],
                    context=context)
        else:
            ids = context['move_line_ids']
        # Or the lines by most old first
        ids.reverse()
        account_move_lines = move_line_pool.browse(
            cr, uid, ids, context=context)

        return account_move_lines


class AccountVoucherLine(models.Model):
    _inherit = "account.voucher.line"

    reference = fields.Char(
        string='Invoice Reference',
        size=64,
        help="The partner reference of this invoice.")
