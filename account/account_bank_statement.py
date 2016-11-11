# -*- coding: utf-8 -*-
#__author__ = 'yenke'

from openerp.osv import fields, osv
from openerp.tools import float_is_zero
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.report import report_sxw
from openerp.tools import float_compare, float_round
import time


class account_bank_statement_line(osv.osv):
    _name = 'account.bank.statement.line'
    _inherit = 'account.bank.statement.line'
    _columns = {
        'date': fields.datetime('Date', required=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic account'),
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
