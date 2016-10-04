# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Arnaud Wüst, Leonardo Pistone
#    Copyright 2009-2014 Camptocamp SA
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
from openerp.osv import fields, orm


class BudgetVersion(orm.Model):

    """ Budget version.

    A budget version is a budget made at a given time for a given company.
    It also can have its own currency """

    _name = "budget.version"
    _description = "Budget versions"

    _order = 'name ASC'

    _columns = {
        'code': fields.char('Code'),
        'name': fields.char('Version Name', required=True),
        'budget_id': fields.many2one('budget.budget',
                                     string='Budget',
                                     required=True,
                                     ondelete='cascade'),
        'currency_id': fields.many2one('res.currency',
                                       string='Currency',
                                       required=True),
        'company_id': fields.many2one('res.company',
                                      string='Company',
                                      required=True),
        'user_id': fields.many2one('res.users', string='User In Charge'),
        'budget_line_ids': fields.one2many('budget.line',
                                           'budget_version_id',
                                           string='Budget Lines'),
        'note': fields.text('Notes'),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'ref_date': fields.date('Reference Date', required=True),
        'is_active': fields.boolean(
            'Active version',
            readonly=True,
            help='Each budget can have no more than one active version.')
    }
