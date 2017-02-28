#__author__ = 'yenke'
import logging
from openerp.osv import fields, osv
import time
from openerp.tools.translate import _

class need_payment(osv.osv_memory):
    _name = 'integc.need.payment'
    _columns = {
        'bank_statement_id': fields.many2one('account.bank.statement', 'Box', domain=[('state', '=', 'open')], required=True),
        'balance_end_real': fields.related('bank_statement_id', 'balance_end_real', type='float', string='Current balance', readonly=True),
    }

    def onchange_bank_statement_id(self, cr, uid, ids, bank_statement_id, context=None):
        context = context or {}
        if not bank_statement_id:
            return {}
        value = {
            'balance_end_real': self.pool.get('account.bank.statement').browse(cr, uid, bank_statement_id, context=context).balance_end_real
        }
        return {'value': value}

    def run(self, cr, uid, ids, context=None):
        active_model = context.get('active_model', False) or False
        active_ids = context.get('active_ids', []) or []

        records = self.pool[active_model].browse(cr, uid, active_ids, context=context)
        for this in self.browse(cr, uid, ids, context=context):
            if records.amount_total > this.balance_end_real:
                raise osv.except_osv(_('Operation not allowed!'), _('The current balance in box is insufficient.'))
            bank_statement = self.pool['account.bank.statement'].browse(cr, uid, this.bank_statement_id.id, context=context)[0]
            for line in records.need_line:
                amount = line.price_subtotal
                account_id = line.product_id.property_account_expense.id
                if not account_id:
                    account_id = line.product_id.categ_id.property_account_expense_categ.id
                if not account_id:
                    raise osv.except_osv(_('Error!'),
                            _('Please define expense account for this product: "%s" (id:%d).') % \
                                (line.product_id.name, line.product_id.id,))
                vals = {
                            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'statement_id': bank_statement.id,
                            'journal_id': bank_statement.journal_id.id,
                            'amount': -amount if amount > 0.0 else amount,
                            'name': line.name,
                            'product_id': line.product_id.id,
                            'partner_id': records.partner_id.id if records.partner_id else None,
                            'analytic_account_id': records.analytic_account_id.id if records.analytic_account_id else None,
                            'account_id': account_id
                        }
                logging.warning(vals)
                self.pool.get('account.bank.statement').write(cr, uid, [bank_statement.id], {'line_ids': [(0, False, vals)]}, context=context)
        self.pool[active_model].write(cr, uid, active_ids, {'state': 'done'})
        return {}


