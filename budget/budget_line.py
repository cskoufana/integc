# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Arnaud Wüst
#    Copyright 2009-2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from operator import itemgetter
from itertools import imap
from openerp.osv import fields, orm
from openerp.addons import decimal_precision as dp   
from datetime import datetime 
from datetime import timedelta
from datetime import date
from dateutil.relativedelta import relativedelta
from time import mktime
import time
import logging
from openerp.tools import ustr, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
from math import fabs

# ---------------------------------------------------------
# Utils
# ---------------------------------------------------------
def strToDate(dt):
    return date(int(dt[0:4]), int(dt[5:7]), int(dt[8:10]))

def strToDatetime(strdate):
    return datetime.strptime(strdate, DEFAULT_SERVER_DATE_FORMAT)


class integc_budget_line(orm.Model):

    """ Budget line.
    A budget version line NOT linked to an analytic account """

    _inherit = "budget.line"

    def _fetch_budget_line_from_aal(self, cr, uid, ids, context=None):
        """
        return the list of budget line to which belong the
        analytic.account.line `ids´
        """
        account_ids = []
        budget_line_obj = self.pool.get('budget.line')
        for aal in self.browse(cr, uid, ids, context=context):
            if aal.account_id and aal.account_id.id not in account_ids:
                account_ids.append(aal.account_id.id)

        line_ids = budget_line_obj.search(cr,
                                          uid,
                                          [('analytic_account_id',
                                            'in',
                                            account_ids)],
                                          context=context)
        return line_ids

    def _get_analytic_amount(self, cr, uid, ids, field_names=None,
                             arg=False, context=None):
        _logger = logging.getLogger(__name__)
        """ Compute the amounts in the analytic account's currency"""
        res = {}
        if field_names is None:
            field_names = []
        currency_obj = self.pool.get('res.currency')
        anl_lines_obj = self.pool.get('account.analytic.line')

        for line in self.browse(cr, uid, ids, context=context):
            anl_account = line.analytic_account_id
            if not anl_account:
                res[line.id] = dict.fromkeys(field_names, 0.0)
                continue
            line_currency_id = line.currency_id.id
            anl_currency_id = line.analytic_currency_id.id
            amount = currency_obj.compute(cr, uid,
                                          line_currency_id,
                                          anl_currency_id,
                                          line.amount,
                                          context=context)
            today = datetime.now()
            _logger.debug('today %s' % (today))
            _logger.debug('line.paid_date %s' % (line.paid_date))
            if line.paid_date:
                if strToDate(line.date_stop) <= strToDate(line.paid_date):
                    theo_amt = 0.00
                else:
                    theo_amt = amount
            else:
                line_timedelta = strToDatetime(line.date_stop) - strToDatetime(line.date_start)
                _logger.debug('line_timedelta %s' % (line_timedelta))
                elapsed_timedelta = today - (strToDatetime(line.date_start))
                _logger.debug('elapsed_timedelta.days %s' % (elapsed_timedelta.days))
                if elapsed_timedelta.days < 0:
                    # If the budget line has not started yet, theoretical amount should be zero
                    theo_amt = 0.00
                elif line_timedelta.days > 0 and today < strToDatetime(line.date_stop):
                    dy = strToDatetime(line.date_stop).year - strToDatetime(line.date_start).year
                    dm = strToDatetime(line.date_stop).month - strToDatetime(line.date_start).month+1
                    linedt = dm+ dy*12
                    _logger.debug('linedt %s' % (linedt))
                    theday = date.today() - relativedelta(months=1)
                    dy2 = theday.year - strToDatetime(line.date_start).year
                    dm2 = theday.month - strToDatetime(line.date_start).month+1
                    linedt2 = dm2 + dy2*12
                    
                    dt = (linedt2 // line.frequency) * line.frequency
                    _logger.debug('dt %s' % (dt))
                    # If today is between the budget line date_start and date_stop
                    theo_amt = (float(dt) / linedt) * amount
                else:
                    theo_amt = amount
            fnl_account_ids = [acc.id for acc
                               in line.budget_item_id.all_account_ids]

            # real amount is the total of analytic lines
            # within the time frame, we'll read it in the
            # analytic account's currency, as for the
            # the budget line so we can compare them
            domain = [('account_id', 'child_of', anl_account.id),
                      ('general_account_id', 'in', fnl_account_ids)]
            if line.date_start:
                domain.append(('date', '>=', line.date_start))
            if line.date_stop:
                domain.append(('date', '<=', line.date_stop))
            anl_line_ids = anl_lines_obj.search(cr, uid, domain,
                                                context=context)
            anl_lines = anl_lines_obj.read(
                cr, uid, anl_line_ids, ['aa_amount_currency'], context=context)
            real = sum([l['aa_amount_currency'] for l in anl_lines])
            if theo_amt <> 0.00:
                perc = float((abs(real) or 0.0) / theo_amt) * 100
            else:
                perc = 0.00
            res[line.id] = {
                'analytic_amount': fabs(amount),
                'theorical_amount': fabs(theo_amt),
                'analytic_real_amount': fabs(real),
                'analytic_diff_amount': fabs(real) - amount,
                'percentage': perc,
            }
        return res
    _columns = {
        'frequency': fields.integer('F',required=True,group_operator="min"),
        'allocation_id': fields.related('budget_item_id', 'allocation_id', type='many2one', relation='budget.allocation.type', string='Allocation',store=True),
        'paid_date': fields.date('Date paiement'),
        'theorical_amount': fields.function(
            _get_analytic_amount,
            type='float',
            digits_compute=dp.get_precision('Account'),
            multi='analytic',
            string="Montant theorique",
            store={
                'budget.line': (lambda self, cr, uid, ids, c: ids,
                                ['amount',
                                 'frequency',
                                 'date_start',
                                 'date_stop',
                                 'analytic_account_id',
                                 'currency_id'], 10),
                'account.analytic.line': (_fetch_budget_line_from_aal,
                                          ['amount',
                                           'unit_amount',
                                           'date'], 10),
            }
        ),
        'percentage': fields.function(
            _get_analytic_amount,
            type='float',
            digits_compute=dp.get_precision('Account'),
            multi='analytic',
            group_operator="avg",
            string="Pourcentage",
            store={
                'budget.line': (lambda self, cr, uid, ids, c: ids,
                                ['amount',
                                 'frequency',
                                 'date_start',
                                 'date_stop',
                                 'analytic_account_id',
                                 'currency_id'], 10),
                'account.analytic.line': (_fetch_budget_line_from_aal,
                                          ['amount',
                                           'unit_amount',
                                           'date'], 10),
            }
        ),
        'analytic_amount': fields.function(
            _get_analytic_amount,
            type='float',
            precision=dp.get_precision('Account'),
            multi='analytic',
            string="In Analytic Amount's Currency",
            store={
                'budget.line': (lambda self, cr, uid, ids, c: ids,
                                ['amount',
                                 'date_start',
                                 'date_stop',
                                 'analytic_account_id',
                                 'currency_id'], 10),
                'account.analytic.line': (_fetch_budget_line_from_aal,
                                          ['amount',
                                           'unit_amount',
                                           'date'], 10),
            }
        ),
        'analytic_real_amount': fields.function(
            _get_analytic_amount,
            type='float',
            precision=dp.get_precision('Account'),
            multi='analytic',
            string="Analytic Real Amount",
            store={
                'budget.line': (lambda self, cr, uid, ids, c: ids,
                                ['amount',
                                 'date_start',
                                 'date_stop',
                                 'analytic_account_id',
                                 'currency_id'], 10),
                'account.analytic.line': (_fetch_budget_line_from_aal,
                                          ['amount',
                                           'unit_amount',
                                           'date'], 10),
            }
        ),
        'analytic_diff_amount': fields.function(
            _get_analytic_amount,
            type='float',
            precision=dp.get_precision('Account'),
            multi='analytic',
            string="Analytic Difference Amount",
            store={
                'budget.line': (lambda self, cr, uid, ids, c: ids,
                                ['amount',
                                 'date_start',
                                 'date_stop',
                                 'analytic_account_id',
                                 'currency_id'], 10),
                'account.analytic.line': (_fetch_budget_line_from_aal,
                                          ['amount',
                                           'unit_amount',
                                           'date'], 10),
            }
        ),
        }
    _defaults = {
        'frequency': 1
    }
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        
        if 'frequency' in fields:
            fields.remove('frequency')
        res = super(integc_budget_line, self).read_group(cr, uid, domain, fields, groupby, offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        if 'analytic_amount' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(cr, uid, line['__domain'], context=context)
                    pending_value = 0.0
                    for current_account in self.browse(cr, uid, lines, context=context):
                        pending_value += current_account.analytic_amount
                    line['analytic_amount'] = pending_value
        if 'analytic_real_amount' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(cr, uid, line['__domain'], context=context)
                    payed_value = 0.0
                    for current_account in self.browse(cr, uid, lines, context=context):
                        payed_value += current_account.analytic_real_amount
                    line['analytic_real_amount'] = payed_value
        if 'theorical_amount' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(cr, uid, line['__domain'], context=context)
                    payed_value = 0.0
                    for current_account in self.browse(cr, uid, lines, context=context):
                        payed_value += current_account.theorical_amount
                    line['theorical_amount'] = payed_value
                    if payed_value <> 0.00:
                        perc = float((abs(line['analytic_real_amount']) or 0.0) / payed_value) * 100
                    else:
                        perc = 0.00
                    line['percentage'] = perc
        return res
    