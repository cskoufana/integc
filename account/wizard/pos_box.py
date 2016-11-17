#__author__ = 'yenke'
from openerp.osv import fields, osv
import time
from openerp.tools.translate import _


class CashBoxIn(osv.osv_memory):
    _name = 'cash.box.in'
    _inherit = 'cash.box.in'

    _columns = {
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic account'),
    }

    def _compute_values_for_statement_line(self, cr, uid, box, record, context=None):
        res = super(CashBoxIn, self)._compute_values_for_statement_line(cr, uid, box, record, context=context)
        res['analytic_account_id'] = box.analytic_account_id.id if box.analytic_account_id else None,
        res['date'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return res


class CashBoxOut(osv.osv_memory):
    _name = 'cash.box.out'
    _inherit = 'cash.box.out'

    _columns = {
        'name': fields.text('Name', required=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic account'),
        'product_id': fields.many2one('product.product', 'Product', domain="[('hr_expense_ok', '=', True)]"),
        'partner_id': fields.many2one('res.partner', 'Partner')
    }

    def _compute_values_for_statement_line(self, cr, uid, box, record, context=None):
        res = super(CashBoxOut, self)._compute_values_for_statement_line(cr, uid, box, record, context=context)
        res['analytic_account_id'] = box.analytic_account_id.id if box.analytic_account_id else None,
        res['date'] = time.strftime('%Y-%m-%d %H:%M:%S')
        res['partner_id'] = box.partner_id.id if box.partner_id else None,
        if box.product_id:
            res['product_id'] = box.product_id.id
            account_id = box.product_id.property_account_expense.id
            if not account_id:
                account_id = box.product_id.categ_id.property_account_expense_categ.id
            if not account_id:
                raise osv.except_osv(_('Error!'),
                        _('Please define expense account for this product: "%s" (id:%d).') % \
                            (box.product_id.name, box.product_id.id,))
            res['account_id'] = account_id
        return res

