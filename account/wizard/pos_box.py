#__author__ = 'yenke'
from openerp.osv import fields, osv
import time


class CashBoxIn(osv.osv_memory):
    _name = 'cash.box.in'
    _inherit = 'cash.box.in'

    _columns = {
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic account'),
    }

    def _compute_values_for_statement_line(self, cr, uid, box, record, context=None):
        res = super(CashBoxIn, self)._compute_values_for_statement_line(cr, uid, box, record, context=context)
        res['analytic_account_id'] = box.analytic_account_id.id if box.analytic_account_id else False,
        res['date'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return res


class CashBoxOut(osv.osv_memory):
    _name = 'cash.box.out'
    _inherit = 'cash.box.out'

    _columns = {
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic account'),
    }

    def _compute_values_for_statement_line(self, cr, uid, box, record, context=None):
        res = super(CashBoxOut, self)._compute_values_for_statement_line(cr, uid, box, record, context=context)
        res['analytic_account_id'] = box.analytic_account_id.id if box.analytic_account_id else False,
        res['date'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return res

