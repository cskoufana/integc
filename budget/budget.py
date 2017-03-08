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
from datetime import date, datetime
import calendar

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class account_analytic_account(orm.Model):
    

    def _budget_line_count(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for account_analytic_account in self.browse(cr, uid, ids, dict(context)):
            res[account_analytic_account.id] = len(account_analytic_account.budget_line_ids)
        return res

    
    _inherit = 'account.analytic.account'

    _columns = {
        'budget_line_count': fields.function(_budget_line_count, type='integer', string="Lignes de budget",),
    }
class budget_budget(orm.Model):

    """ Budget Model. The module's main object.  """
    _inherit = "budget.budget"
    _columns = {
        'analytic_account_id': fields.many2one(
            'account.analytic.account', 'Contract/Analytic',
            help="Link this project to an analytic account if you need financial management on projects. "
                 "It enables you to connect projects with budgets, planning, cost and revenue analysis, timesheets on projects, etc.",
            ),
    }
    def on_change_start_date(self, cr, uid, ids, start_date_str, context=None):
        if start_date_str : 
            start_date = datetime.strptime(start_date_str, DATE_FORMAT)
    
            last_day_of_month = calendar.monthrange(start_date.year,
                                                    start_date.month)[1]
    
            end_date = datetime(
                year=start_date.year,
                month=start_date.month,
                day=last_day_of_month)
    
            end_date_str = date.strftime(end_date, DATE_FORMAT)
    
            return {'value': {'end_date': end_date_str}}
        return {'value' : {}}
