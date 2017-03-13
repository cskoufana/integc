# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp import tools
from openerp.osv import fields,osv
import openerp.addons.decimal_precision as dp

class account_voucher_report(osv.osv):
    _name = "account.voucher.report"
    _description = "Journal Voucher analysis"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Effective Date', readonly=True),  # TDE FIXME master: rename into date_effective
        'ref': fields.char('Reference', readonly=True),
        'name': fields.char('Description', readonly=True),
        'nbr': fields.integer('Nbr of entries', readonly=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account'), readonly=True),
        'period_id': fields.many2one('account.period', 'Period', readonly=True),
        'account_id': fields.many2one('account.account', 'Account', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True),
        'product_type' : fields.selection([
            ('consu', 'Consommable'),
            ('product', 'Product')
            ], 'Product Type', readonly=True),
        'journal_type' : fields.selection([
            ('bank', 'Bank'),
            ('cash', 'Cash')
            ], 'Journal Type', readonly=True),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'partner_id': fields.many2one('res.partner','Partner', readonly=True),
        'user_id': fields.many2one('res.users','Responsable', readonly=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
    }

    _order = 'date desc'

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        period_obj = self.pool.get('account.period')
        for arg in args:
            if arg[0] == 'period_id' and arg[2] == 'current_period':
                current_period = period_obj.find(cr, uid, context=context)[0]
                args.append(['period_id','in',[current_period]])
                break
            elif arg[0] == 'period_id' and arg[2] == 'current_year':
                current_year = fiscalyear_obj.find(cr, uid)
                ids = fiscalyear_obj.read(cr, uid, [current_year], ['period_ids'])[0]['period_ids']
                args.append(['period_id','in',ids])
        for a in [['period_id','in','current_year'], ['period_id','in','current_period']]:
            if a in args:
                args.remove(a)
        return super(account_voucher_report, self).search(cr, uid, args=args, offset=offset, limit=limit, order=order,
            context=context, count=count)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,lazy=True):
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        period_obj = self.pool.get('account.period')
        if context.get('period', False) == 'current_period':
            current_period = period_obj.find(cr, uid, context=context)[0]
            domain.append(['period_id','in',[current_period]])
        elif context.get('year', False) == 'current_year':
            current_year = fiscalyear_obj.find(cr, uid)
            ids = fiscalyear_obj.read(cr, uid, [current_year], ['period_ids'])[0]['period_ids']
            domain.append(['period_id','in',ids])
        else:
            domain = domain
        return super(account_voucher_report, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby,lazy)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_voucher_report')
        cr.execute(""" 
            create or replace view account_voucher_report as (
            (select
                a.journal_id || '' || l.id as id,
                l.date as date,
                l.ref as ref,
                a.state as state,
                l.partner_id as partner_id,
                l.product_id as product_id,
                a.company_id as company_id,
                a.journal_id as journal_id,
                p.fiscalyear_id as fiscalyear_id,
                a.period_id as period_id,
                l.account_id as account_id,
                po.type as product_type,
                j.type as journal_type,
                l.analytic_account_id as analytic_account_id,
                1 as nbr,
                @l.amount as amount,
                l.name as name,
                a.user_id as user_id
            from
                account_bank_statement_line l
                left join account_bank_statement a on (l.statement_id = a.id)
                left join account_period p on (a.period_id=p.id)
                left join account_journal j on (j.id = a.journal_id)
                left join product_template po on (po.id = l.product_id)
                    where a.state not in ( 'draft','cancel') and j.type in ('bank','cash') and po.type not in ('service')
                )
                
                union (
                select
                l.journal_id || '' || l.id as id,
                l.date as date,
                l.reference as ref,
                l.state as state,
                l.partner_id as partner_id,
                l.product_id as product_id,
                l.company_id as company_id,
                l.journal_id as journal_id,
                p.fiscalyear_id as fiscalyear_id,
                l.period_id as period_id,
                l.account_id as account_id,
                po.type as product_type,
                j.type as journal_type,
                l.analytic_account_id as analytic_account_id,
                1 as nbr,
                @l.amount as amount,
                l.narration as name,
                l.create_uid as user_id
            from
                account_voucher l
                left join account_period p on (l.period_id=p.id)
                left join account_journal j on (j.id = l.journal_id)
                left join product_template po on (po.id = l.product_id)
                    where l.state not in ( 'draft','cancel') and j.type in ('bank','cash') and po.type not in ('service')
                )
                
                )
        """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
