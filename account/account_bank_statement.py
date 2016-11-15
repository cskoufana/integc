# -*- coding: utf-8 -*-
#__author__ = 'yenke'

from openerp.osv import fields, osv
from openerp.tools import float_is_zero
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.report import report_sxw
from openerp.tools import float_compare, float_round
import time

class account_bank_statement(osv.osv):

    _inherit = 'account.bank.statement'

    def button_confirm_cash(self, cr, uid, ids, context=None):
        absl_proxy = self.pool.get('account.bank.statement.line')

        TABLES = ((_('Profit'), 'profit_account_id'), (_('Loss'), 'loss_account_id'),)

        for obj in self.browse(cr, uid, ids, context=context):
            if obj.difference == 0.0:
                continue
            elif obj.difference < 0.0:
                account = obj.journal_id.loss_account_id
                name = _('Loss')
                if not obj.journal_id.loss_account_id:
                    raise osv.except_osv(_('Error!'), _('There is no Loss Account on the journal %s.') % (obj.journal_id.name,))
            else: # obj.difference > 0.0
                account = obj.journal_id.profit_account_id
                name = _('Profit')
                if not obj.journal_id.profit_account_id:
                    raise osv.except_osv(_('Error!'), _('There is no Profit Account on the journal %s.') % (obj.journal_id.name,))

            values = {
                'statement_id' : obj.id,
                'journal_id' : obj.journal_id.id,
                'account_id' : account.id,
                'amount' : obj.difference,
                'name' : name,
            }
            absl_proxy.create(cr, uid, values, context=context)

        return self.button_confirm_bank(cr, uid, ids, context=context)

    def button_confirm_bank(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error!'), _('Please verify that an account is defined in the journal.'))
            for line in st.move_line_ids:
                if line.state != 'valid':
                    raise osv.except_osv(_('Error!'), _('The account entries lines are not in valid state.'))
            move_ids = []
            for st_line in st.line_ids:
                if not st_line.amount:
                    continue
                if st_line.account_id and not st_line.journal_entry_id.id:
                    #make an account move as before
                    vals = {
                        'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                        'credit': st_line.amount > 0 and st_line.amount or 0.0,
                        'account_id': st_line.account_id.id,
                        'name': st_line.name,
                        'analytic_account_id': st_line.analytic_account_id.id if st_line.analytic_account_id else None,
                    }
                    self.pool.get('account.bank.statement.line').process_reconciliation(cr, uid, st_line.id, [vals], context=context)
                elif not st_line.journal_entry_id.id:
                    raise osv.except_osv(_('Error!'), _('All the account entries lines must be processed in order to close the statement.'))
                move_ids.append(st_line.journal_entry_id.id)
            if move_ids:
                self.pool.get('account.move').post(cr, uid, move_ids, context=context)
            self.message_post(cr, uid, [st.id], body=_('Statement %s confirmed, journal items were created.') % (st.name,), context=context)
        self.link_bank_to_partner(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm', 'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")}, context=context)



class account_bank_statement_line(osv.osv):
    _name = 'account.bank.statement.line'
    _inherit = 'account.bank.statement.line'
    _columns = {
        'date': fields.datetime('Date', required=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic account'),
        'product_id': fields.many2one('product.product', 'Product')
    }

    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    def print_receipt(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        datas = {
            'ids': ids,
            'model': 'account.bank.statement.line',
            'form': self.read(cr, uid, ids, context=context)
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.box',
            'datas': datas,
            'nodestroy': True
        }


