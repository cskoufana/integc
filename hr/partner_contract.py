# -*- coding: utf-8 -*-
#__author__ = 'yenke'


from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from openerp import pooler
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp import netsvc
import logging


class integc_hr_partner_contract(osv.osv):
    _name = "integc.hr.partner.contract"
    #_inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Partner contract"
    #_track = {
    #    'state': {
    #        'sale.mt_order_confirmed': lambda self, cr, uid, obj, ctx=None: obj['state'] in ['manual', 'progress'],
    #        'sale.mt_order_sent': lambda self, cr, uid, obj, ctx=None: obj['state'] in ['sent']
    #    },
    #}

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'date': fields.date.context_today(self, cr, uid, context=context),
            'state': 'draft',
            'invoice_ids': [],
            'date_confirm': False,
            'name' : self.pool.get('ir.sequence').get(cr, uid, 'integc.hr.partner.contract'),
        })
        return super(integc_hr_partner_contract, self).copy(cr, uid, id, default, context=context)

    def _invoice_count(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for record in self.browse(cr, uid, ids, dict(context, active_test=False)):
            res[record.id] = len(record.invoice_ids)
        return res

    def _amount_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0.0)/100.0), line.product_uom_qty, line.product_id, line.contract_id.partner_id)['taxes']:
            val += c.get('amount', 0.0)
        return val

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'balance': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.contract_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context=context)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['balance'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res


    def _invoiced_rate(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for sale in self.browse(cursor, user, ids, context=context):
            if sale.invoiced:
                res[sale.id] = 100.0
                continue
            tot = 0.0
            for invoice in sale.invoice_ids:
                if invoice.state not in ('draft', 'cancel'):
                    tot += invoice.amount_untaxed
            if tot:
                res[sale.id] = min(100.0, tot * 100.0 / (sale.amount_untaxed or 1.00))
            else:
                res[sale.id] = 0.0
        return res

    def _invoice_exists(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for sale in self.browse(cursor, user, ids, context=context):
            res[sale.id] = False
            if sale.invoice_ids:
                res[sale.id] = True
        return res

    def _invoiced(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for sale in self.browse(cursor, user, ids, context=context):
            res[sale.id] = True
            invoice_existence = False
            for invoice in sale.invoice_ids:
                if invoice.state!='cancel':
                    invoice_existence = True
                    if invoice.state != 'paid':
                        res[sale.id] = False
                        break
            if not invoice_existence or sale.state == 'manual':
                res[sale.id] = False
        return res

    def _amount_balance(self, cr, uid, ids, context=None):
        res = []
        invoice_ids = []
        cr.execute('SELECT rel.invoice_id FROM integc_hr_partner_contract_invoice_rel AS rel WHERE rel.contract_id = %s' % ids[0])
        res = cr.fetchall()
        for x in res:
            invoice_ids.append(x[0])
        #invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('id', 'in', invoice_ids), ('state', 'in', ('open','paid'))], context=context)
        balance = 0.0
        for invoice in self.pool.get('account.invoice').browse(cr, uid, invoice_ids, context=context):
            if invoice.state not in ['draft', 'cancel']:
                balance += invoice.amount_total
        #logging.warning(balance)
        this = self.browse(cr, uid, ids[0], context=context)
        #logging.warning('Montant Contrat : %s - Balance : %s' % (this.amount_total, balance))
        return this.amount_total - balance

    def _get_amount_balance(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        #contract_ids = []
        invoice_ids = []
        balance = 0.0
        #cond = 'in' if len(ids) > 1 else '='
        cond = '='
        values = ids[0]
        if len(ids) > 1 :
            values = tuple(ids)
            cond = 'in'
        #cr.execute('SELECT rel.contract_id FROM integc_hr_partner_contract_invoice_rel AS rel WHERE rel.invoice_id = %s' % ids[0])
        #for x in cr.fetchall():
        #    contract_ids.append(x[0])
        #if contract_ids:
        cr.execute('SELECT rel.invoice_id FROM integc_hr_partner_contract_invoice_rel AS rel WHERE rel.contract_id %s %s' % (cond,values))
        for x in cr.fetchall():
            invoice_ids.append(x[0])
        for invoice in self.pool.get('account.invoice').browse(cr, uid, invoice_ids, context=context):
            if invoice.state not in ['draft', 'cancel']:
                balance += invoice.amount_total
        for record in self.browse(cr, uid, ids, context=context):
            #res[record.id] = self._amount_balance(cr, uid, ids, context=context)
            res[record.id] = record.amount_total - balance
        return res

    def _set_amount_balance(self, cr, uid, ids, name, args, context=None):
        balance = self._amount_balance(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'balance': balance}, context=context)
        return balance

    def _invoiced_search(self, cursor, user, obj, name, args, context=None):
        if not len(args):
            return []
        clause = ''
        contract_clause = ''
        no_invoiced = False
        for arg in args:
            if arg[1] == '=':
                if arg[2]:
                    clause += 'AND inv.state = \'paid\''
                else:
                    clause += 'AND inv.state != \'cancel\' AND sale.state != \'cancel\'  AND inv.state <> \'paid\'  AND rel.contract_id = contract.id '
                    contract_clause = ',  integc_hr_partner_contract AS contract '
                    no_invoiced = True

        cursor.execute('SELECT rel.contract_id ' \
                'FROM integc_hr_partner_contract_invoice_rel AS rel, account_invoice AS inv '+ contract_clause + \
                'WHERE rel.invoice_id = inv.id ' + clause)
        res = cursor.fetchall()
        if no_invoiced:
            cursor.execute('SELECT contract.id ' \
                    'FROM integc_hr_partner_contract AS contract ' \
                    'WHERE contract.id NOT IN ' \
                        '(SELECT rel.contract_id ' \
                        'FROM integc_hr_partner_contract_invoice_rel AS rel) and contract.state != \'cancel\'')
            res.extend(cursor.fetchall())
        if not res:
            return [('id', '=', 0)]
        return [('id', 'in', [x[0] for x in res])]

    def _search_balance(self, cr, uid, obj, name, args, context):
        ids = set()
        for cond in args:
            amount = cond[2]
            if isinstance(cond[2],(list,tuple)):
                if cond[1] in ['in','not in']:
                    amount = tuple(cond[2])
                else:
                    continue
            else:
                if cond[1] in ['=like', 'like', 'not like', 'ilike', 'not ilike', 'in', 'not in', 'child_of']:
                    continue

            cr.execute("SELECT rel.contract_id FROM integc_hr_partner_contract AS c, account_invoice AS i, integc_hr_partner_contract_invoice_rel AS rel WHERE rel.contract_id = c.id and i.id = re.invoice_id and i.state not in ('draft', 'cancel') having sum(amount_total) %s %%s" % (cond[1]),(amount,))
            #cr.execute("select id from integc_hr_partner_contract group by id having balance %s %%s" % (cond[1]),(amount,))
            res_ids = set(id[0] for id in cr.fetchall())
            ids = ids and (ids & res_ids) or res_ids
        if ids:
            return [('id', 'in', tuple(ids))]
        return [('id', '=', '0')]

    def _get_contract(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('integc.hr.partner.contract.line').browse(cr, uid, ids, context=context):
            result[line.contract_id.id] = True
        return result.keys()

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        return company_id

    def _get_first_date(self, cr, uid, id, name, value, args=None, context=None):
        return time.strftime('%Y-%m-01')

    def _get_last_date(self, cr, uid, id, name, value, args=None, context=None):
        return str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]

    def _get_contract_from_invoice(self, cr, uid, ids, context=None):
        res = {}
        cond = '='
        values = ids[0]
        if len(ids) > 1 :
            values = tuple(ids)
            cond = 'in'
        cr.execute('SELECT rel.contract_id FROM integc_hr_partner_contract_invoice_rel as rel WHERE rel.invoice_id %s %s' % (cond,values))
        for x in cr.fetchall():
            res[x[0]] = True
        return res.keys()

    _columns = {
        'name': fields.char('Contract Reference', size=64, readonly=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('waiting_director', 'Waiting for signature of director'),
            ('waiting_partner', 'Waiting for signature of partner'),
            ('progress', 'Progress'),
            ('complete', 'Completed'),
            ('cancel', 'Cancelled')
            ], 'Status', readonly=True, track_visibility='onchange',select=True),
        'type': fields.selection([
            ('expert', 'Expert'),
            ('outsourcing', 'Outsourcing'),
        ], string='Type', select=True, required=True),
        'date': fields.date('Date', required=True, readonly=True, select=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True, help="Date on which contract is created."),
        'date_confirm': fields.date('Confirmation Date', readonly=True, select=True, help="Date on which contract is confirmed."),
        'date_signature': fields.date('Date Signature', readonly=True, select=True, help="Date on which contract is signed."),
        'date_start': fields.date('Start Date', required=True),
        'date_end': fields.date('End Date'),
        'user_id': fields.many2one('res.users', 'User', select=True, track_visibility='onchange'),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, change_default=True, select=True, track_visibility='always'),
        'partner_invoice_id': fields.many2one('res.partner', 'Invoice Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Invoice address for current sales order."),
        'partner_shipping_id': fields.many2one('res.partner', 'Delivery Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Delivery address for current contract."),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Pricelist for current contract."),
        'currency_id': fields.related('pricelist_id', 'currency_id', type="many2one", relation="res.currency", string="Currency", readonly=True, required=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic account', help="The analytic account related to a contract."),
        'project_id': fields.many2one('project.project', 'Project', help="The project related to a contract."),
        'contract_line': fields.one2many('integc.hr.partner.contract.line', 'contract_id', 'Contract Lines'),
        'invoice_ids': fields.many2many('account.invoice', 'integc_hr_partner_contract_invoice_rel', 'contract_id', 'invoice_id', 'Invoices', readonly=True, help="This is the list of invoices that have been generated for this contract. The same contract may have been invoiced in several times (by line for example)."),
        'invoiced_rate': fields.function(_invoiced_rate, string='Invoiced Ratio', type='float'),
        'invoiced': fields.function(_invoiced, string='Paid',
            fnct_search=_invoiced_search, type='boolean', help="It indicates that an invoice has been paid."),
        'invoice_exists': fields.function(_invoice_exists, string='Invoiced',
            fnct_search=_invoiced_search, type='boolean', help="It indicates that contract has at least one invoice."),
        'note': fields.text('Terms and conditions'),

        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'integc.hr.partner.contract': (lambda self, cr, uid, ids, c={}: ids, ['contract_line'], 10),
                'integc.hr.partner.contract.line': (_get_contract, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'integc.hr.partner.contract': (lambda self, cr, uid, ids, c={}: ids, ['contract_line'], 10),
                'integc.hr.partner.contract.line': (_get_contract, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'integc.hr.partner.contract': (lambda self, cr, uid, ids, c={}: ids, ['contract_line'], 10),
                'integc.hr.partner.contract.line': (_get_contract, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The total amount."),

        'balance': fields.function(_get_amount_balance, digits_compute=dp.get_precision('Account'), string='Balance',
            store={
                'integc.hr.partner.contract': (lambda self, cr, uid, ids, c={}: ids, [], 10),
                'integc.hr.partner.contract.line': (_get_contract, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
                'account.invoice': (_get_contract_from_invoice, ['state'], 10),
            }),

        'payment_term': fields.many2one('account.payment.term', 'Payment Term'),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position'),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'invoicing_mode': fields.selection([
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annual', 'Annual')
        ], string='Invoicing Mode', required=True),
        'attachment_ids': fields.many2many("ir.attachment", "integc_hr_partner_contract_attachment_rel",
                                           "attachment_id", "contract_id", "Attachments"),
        'invoice_count': fields.function(_invoice_count, type='integer', string="Invoices",),
    }
    _defaults = {
        'date': fields.date.context_today,
        'date_start': fields.date.context_today,
        'state': 'draft',
        'user_id': lambda obj, cr, uid, context: uid,
        'company_id': _get_default_company,
        'partner_invoice_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['invoice'])['invoice'],
        'partner_shipping_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['delivery'])['delivery'],
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Contract Reference must be unique per Company!'),
    ]
    _order = 'date desc, id desc'

    #def write(self, cr, uid, ids, values, context=None):
    #    #if 'balance' not in values:
    #    #values['balance'] = self._amount_balance(cr, uid, ids, context=None)
    #    return super(integc_hr_partner_contract, self).write(cr, uid, ids, values, context=context)

    # Form filling
    def unlink(self, cr, uid, ids, context=None):
        contracts = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in contracts:
            if s['state'] in ['draft', 'cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid Action!'), _('In order to delete a confirmed contract, you must cancel it before!'))

        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)

    #def copy_quotation(self, cr, uid, ids, context=None):
    #    id = self.copy(cr, uid, ids[0], context=None)
    #    view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'view_order_form')
    #    view_id = view_ref and view_ref[1] or False,
    #    return {
    #        'type': 'ir.actions.act_window',
    #        'name': _('Sales Order'),
    #        'res_model': 'sale.order',
    #        'res_id': id,
    #        'view_type': 'form',
    #        'view_mode': 'form',
    #        'view_id': view_id,
    #        'target': 'current',
    #        'nodestroy': True,
    #    }

    def onchange_pricelist_id(self, cr, uid, ids, pricelist_id, contract_lines, context=None):
        context = context or {}
        if not pricelist_id:
            return {}
        value = {
            'currency_id': self.pool.get('product.pricelist').browse(cr, uid, pricelist_id, context=context).currency_id.id
        }
        return {'value': value}


    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        if not part:
            return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False}}

        part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
        addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        payment_term = part.property_payment_term and part.property_payment_term.id or False
        fiscal_position = part.property_account_position and part.property_account_position.id or False
        dedicated_salesman = part.user_id and part.user_id.id or uid
        val = {
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'payment_term': payment_term,
            'fiscal_position': fiscal_position,
            'user_id': dedicated_salesman,
        }
        if pricelist:
            val['pricelist_id'] = pricelist
        return {'value': val}

    def create(self, cr, uid, vals, context=None):
        if 'name' not in vals:
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'integc.hr.partner.contract')
        return super(integc_hr_partner_contract, self).create(cr, uid, vals, context=context)

    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def _prepare_invoice(self, cr, uid, contract, lines, context=None):
        """Prepare the dict of values to create the new invoice for a
           contract. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: sale.order record to invoice
           :param list(int) line: list of invoice line IDs that must be
                                  attached to the invoice
           :return: dict of value to create() the invoice
        """
        if context is None:
            context = {}
        #journal_ids = self.pool.get('account.journal').search(cr, uid,
        #    [('type', '=', 'sale'), ('company_id', '=', contract.company_id.id)],
        #    limit=1)
        journal_ids = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'integc', 'account_journal_payroll')
        if not journal_ids:
            raise osv.except_osv(_('Error!'),
                _('Please define sales journal for this company: "%s" (id:%d).') % (contract.company_id.name, contract.company_id.id))
        invoice_vals = {
            'name': '',
            'origin': contract.name,
            'type': 'in_invoice',
            'reference': contract.name,
            'account_id': contract.partner_id.property_account_receivable.id,
            'partner_id': contract.partner_invoice_id.id,
            'journal_id': journal_ids[1],
            'invoice_line': [(6, 0, lines)],
            'currency_id': contract.pricelist_id.currency_id.id,
            'comment': contract.note,
            'fiscal_position': contract.fiscal_position.id or contract.partner_id.property_account_position.id,
            'date_invoice': context.get('date_invoice', False),
            'company_id': contract.company_id.id,
            'user_id': uid
        }

        #invoice_vals.update(self._inv_get(cr, uid, contract, context=context))
        return invoice_vals

    def _make_invoice(self, cr, uid, contract, lines, context=None):
        inv_obj = self.pool.get('account.invoice')
        obj_invoice_line = self.pool.get('account.invoice.line')
        if context is None:
            context = {}
        #invoiced_sale_line_ids = self.pool.get('integc.hr.partner.contract.line').search(cr, uid, [('contract_id', '=', contract.id), ('invoiced', '=', True)], context=context)
        #from_line_invoice_ids = []
        #for invoiced_sale_line_id in self.pool.get('integc.hr.partner.contract.line').browse(cr, uid, invoiced_sale_line_ids, context=context):
        #    for invoice_line_id in invoiced_sale_line_id.invoice_lines:
        #        if invoice_line_id.invoice_id.id not in from_line_invoice_ids:
        #            from_line_invoice_ids.append(invoice_line_id.invoice_id.id)
        #for preinv in contract.invoice_ids:
        #    if preinv.state not in ('cancel',) and preinv.id not in from_line_invoice_ids:
        #        for preline in preinv.invoice_line:
        #            inv_line_id = obj_invoice_line.copy(cr, uid, preline.id, {'invoice_id': False, 'price_unit': -preline.price_unit})
        #            lines.append(inv_line_id)
        inv = self._prepare_invoice(cr, uid, contract, lines, context=context)
        inv_id = inv_obj.create(cr, uid, inv, context=context)
        #data = inv_obj.onchange_payment_term_date_invoice(cr, uid, [inv_id], inv['payment_term'], time.strftime(DEFAULT_SERVER_DATE_FORMAT))
        #if data.get('value', False):
        #    inv_obj.write(cr, uid, [inv_id], data['value'], context=context)
        inv_obj.button_compute(cr, uid, [inv_id])
        return inv_id


    def manual_invoice(self, cr, uid, ids, context=None):
        """ create invoices for the given contracts (ids), and open the form
            view of one of the newly created invoices
        """
        mod_obj = self.pool.get('ir.model.data')
        #wf_service = netsvc.LocalService("workflow")

        # create invoices through the contracts' workflow
        inv_ids = set(inv.id for contract in self.browse(cr, uid, ids, context) for inv in contract.invoice_ids)


        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
        res_id = res and res[1] or False,

        return {
            'name': _('Customer Invoices'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }

    def action_view_invoice(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing invoices of given contract ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree2')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of invoices to display
        inv_ids = []
        for so in self.browse(cr, uid, ids, context=context):
            inv_ids += [invoice.id for invoice in so.invoice_ids]
        #choose the view_mode accordingly
        if len(inv_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, inv_ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = inv_ids and inv_ids[0] or False
        return result

    def test_no_product(self, cr, uid, contract, context):
        for line in contract.contract_line:
            if line.product_id and (line.product_id.type != 'service'):
                return False
        return True

    def create_invoice(self, cr, uid, ids, grouped=False, states=None, date_invoice = False, context=None):
        #if states is None:
        #    states = ['confirmed', 'done', 'exception']
        balance = self._amount_balance(cr, uid, ids, context=context)
        if balance <= 0.0:
            raise osv.except_osv(_('Operation not allowed!'), _('You cannot create invoice for that contract with balance %s' % balance))
        res = False
        invoices = {}
        invoice_ids = []
        invoice = self.pool.get('account.invoice')
        obj_contract_line = self.pool.get('integc.hr.partner.contract.line')
        partner_currency = {}
        if context is None:
            context = {}
        # If date was specified, use it as date invoiced, usefull when invoices are generated this month and put the
        # last day of the last month as invoice date
        if date_invoice:
            context['date_invoice'] = date_invoice
        for o in self.browse(cr, uid, ids, context=context):
            currency_id = o.pricelist_id.currency_id.id
            if (o.partner_id.id in partner_currency) and (partner_currency[o.partner_id.id] != currency_id):
                raise osv.except_osv(
                    _('Error!'),
                    _('You cannot group sales having different currencies for the same partner.'))

            partner_currency[o.partner_id.id] = currency_id
            lines = []
            for line in o.contract_line:
                #if line.invoiced:
                #    continue
                #elif (line.state in states):
                #    lines.append(line.id)
                lines.append(line.id)
            created_lines = obj_contract_line.invoice_line_create(cr, uid, lines)
            #logging.warning('created_lines : %s' % created_lines)
            if created_lines:
                invoices.setdefault(o.partner_invoice_id.id or o.partner_id.id, []).append((o, created_lines))
        if not invoices:
            for o in self.browse(cr, uid, ids, context=context):
                for i in o.invoice_ids:
                    if i.state == 'draft':
                        return i.id
        #logging.warning(invoices.values())
        for val in invoices.values():
            if grouped:
                res = self._make_invoice(cr, uid, val[0][0], reduce(lambda x, y: x + y, [l for o, l in val], []), context=context)
                invoice_ref = ''
                for o, l in val:
                    invoice_ref += o.name + '|'
                    cr.execute('insert into integc_hr_partner_contract_invoice_rel (contract_id,invoice_id) values (%s,%s)', (o.id, res))
                #remove last '|' in invoice_ref
                if len(invoice_ref) >= 1:
                    invoice_ref = invoice_ref[:-1]
                invoice.write(cr, uid, [res], {'origin': invoice_ref, 'name': invoice_ref})
            else:
                for order, il in val:
                    res = self._make_invoice(cr, uid, order, il, context=context)
                    invoice_ids.append(res)
                    cr.execute('insert into integc_hr_partner_contract_invoice_rel (contract_id,invoice_id) values (%s,%s)', (order.id, res))
        #mod_obj = self.pool.get('ir.model.data')
        #act_obj = self.pool.get('ir.actions.act_window')
        #result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree2')
        #id = result and result[1] or False
        #result = act_obj.read(cr, uid, [id], context=context)[0]
        ###result['domain'] = "[('id','in', [" + ','.join(map(str, res)) + "])]"
        ##result['domain'] = "[('id','in', [" + str(res) + "])]"
        #res_ = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
        #result['views'] = [(res_ and res_[1] or False, 'form')]
        #result['res_id'] = res and res[0] or False
        #return result
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree2')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of invoices to display

        #choose the view_mode accordingly
        if len(invoice_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, invoice_ids))+"])]"
        else:
            res_ = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
            result['views'] = [(res_ and res_[1] or False, 'form')]
            result['res_id'] = res or False
        return result

    def action_invoice_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'invoice_except'}, context=context)
        return True

    def action_invoice_end(self, cr, uid, ids, context=None):
        for this in self.browse(cr, uid, ids, context=context):
            for line in this.contract_line:
                if line.state == 'exception':
                    line.write({'state': 'confirmed'})
            if this.state == 'invoice_except':
                this.write({'state': 'progress'})
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}
        contract_line_obj = self.pool.get('integc.hr.partner.contract.line')
        for sale in self.browse(cr, uid, ids, context=context):
            for inv in sale.invoice_ids:
                if inv.state not in ('draft', 'cancel'):
                    raise osv.except_osv(
                        _('Cannot cancel this contract!'),
                        _('First cancel all invoices attached to this contract.'))
            for r in self.read(cr, uid, ids, ['invoice_ids']):
                for inv in r['invoice_ids']:
                    wf_service.trg_validate(uid, 'account.invoice', inv, 'invoice_cancel', cr)
            contract_line_obj.write(cr, uid, [l.id for l in  sale.contract_line],
                    {'state': 'cancel'})
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True

    def action_progress(self, cr, uid, ids, context=None):
        context = context or {}
        for c in self.browse(cr, uid, ids):
            #if not c.contract_line:
            #    raise osv.except_osv(_('Error!'),_('You cannot confirm a contract which has no line.'))
            #noprod = self.test_no_product(cr, uid, c, context)
            self.write(cr, uid, [c.id], {'state': 'progress', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
            self.pool.get('integc.hr.partner.contract.line').button_confirm(cr, uid, [x.id for x in c.contract_line])
        return True

    def action_waiting_partner(self, cr, uid, ids, context=None):
        context = context or {}
        for c in self.browse(cr, uid, ids):
            if not c.contract_line:
                raise osv.except_osv(_('Error!'),_('You cannot confirm a contract which has no line.'))
            noprod = self.test_no_product(cr, uid, c, context)
            self.write(cr, uid, [c.id], {'state': 'waiting_partner', 'date_signature': fields.date.context_today(self, cr, uid, context=context)})
        return True

    def action_waiting_director(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'waiting_director'}, context=context)

    def action_complete(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'complete'}, context=context)

    def onchange_analytic_account_id(self, cr, uid, ids, value, context=None):
        res = {'project_id': False}
        if value:
            project_ids = self.pool.get('project.project').search(cr, uid, [('analytic_account_id', '=', value)], context=context)
            res = {
                'project_id': project_ids and project_ids[0]
            }
        return {'value': res}

    def scheduler_close_contract(self, cr, uid, context=None):
        cr.execute("select c.id from integc_hr_partner_contract c where c.date_end is not null and c.state = 'progress' and c.date_end < '%s'" % time.strftime('%Y-%m-%d'))
        ids = [x[0] for x in cr.fetchall()]
        if ids:
            self.write(cr, uid, ids, {'state', '=', 'complete'})
        return True

    def run_scheduler(self, cr, uid, context=None):
        self.scheduler_close_contract(cr, uid, context=context)
        return True

    def get_contract_balance(self, cr, uid, invoice_id, context=None):
        cr.execute('SELECT rel.contract_id FROM integc_hr_partner_contract_invoice_rel AS rel WHERE rel.invoice_id = %s' % invoice_id)
        res = cr.fetchall()
        balance = 0.0
        contract_name = ''
        if res:
            for x in res:
                for record in self.browse(cr, uid, [x[0]]):
                    balance = record.balance
                    contract_name = record.name
        return contract_name,balance


integc_hr_partner_contract()


class integc_hr_partner_contract_line(osv.osv):

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.contract_id.partner_id)
            cur = line.contract_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res

    def _get_uom_id(self, cr, uid, *args):
        try:
            proxy = self.pool.get('ir.model.data')
            result = proxy.get_object_reference(cr, uid, 'product', 'product_uom_unit')
            return result[1]
        except Exception as ex:
            return False

    def _fnct_line_invoiced(self, cr, uid, ids, field_name, args, context=None):
        res = dict.fromkeys(ids, False)
        for this in self.browse(cr, uid, ids, context=context):
            res[this.id] = this.invoice_lines and \
                all(iline.invoice_id.state != 'cancel' for iline in this.invoice_lines)
        return res

    def _contract_lines_from_invoice(self, cr, uid, ids, context=None):
        # direct access to the m2m table is the less convoluted way to achieve this (and is ok ACL-wise)
        cr.execute("""SELECT DISTINCT cl.id FROM integc_hr_partner_contract_invoice_rel rel JOIN
                                                  integc_hr_partner_contract_line cl ON (cl.contract_id = rel.contract_id)
                                    WHERE rel.invoice_id = ANY(%s)""", (list(ids),))
        return [i[0] for i in cr.fetchall()]

    _name = 'integc.hr.partner.contract.line'
    _description = 'Partner contract line'
    _columns = {
        'contract_id': fields.many2one('integc.hr.partner.contract', 'Partner Contract', required=True, ondelete='cascade', select=True, readonly=True, states={'draft':[('readonly',False)]}),
        'name': fields.text('Description', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of contract lines."),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True),
        'invoice_lines': fields.many2many('account.invoice.line', 'integc_hr_partner_contract_line_invoice_rel', 'contract_line_id', 'invoice_id', 'Invoice Lines', readonly=True),
        'invoiced': fields.function(_fnct_line_invoiced, string='Invoiced', type='boolean',
            store={
                'account.invoice': (_contract_lines_from_invoice, ['state'], 10),
                'integc.hr.partner.contract.line': (lambda self,cr,uid,ids,ctx=None: ids, ['invoice_lines'], 10)}),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price'), readonly=True, states={'draft': [('readonly', False)]}),
        'type': fields.selection([('make_to_stock', 'from stock'), ('make_to_order', 'on order')], 'Procurement Method', required=True, readonly=True, states={'draft': [('readonly', False)]},
         help="From stock: When needed, the product is taken from the stock or we wait for replenishment.\nOn order: When needed, the product is purchased or produced."),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
        'tax_id': fields.many2many('account.tax', 'integc_hr_partner_contract_line_tax', 'contract_line_id', 'tax_id', 'Taxes', readonly=True, states={'draft': [('readonly', False)]}),
        'address_allotment_id': fields.many2one('res.partner', 'Allotment Partner',help="A partner to whom the particular product needs to be allotted."),
        'product_uom_qty': fields.float('Quantity', digits_compute= dp.get_precision('Product UoS'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uos_qty': fields.float('Quantity (UoS)' ,digits_compute= dp.get_precision('Product UoS'), readonly=True, states={'draft': [('readonly', False)]}),
        'product_uos': fields.many2one('product.uom', 'Product UoS'),
        'discount': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount'), readonly=True, states={'draft': [('readonly', False)]}),
        'th_weight': fields.float('Weight', readonly=True, states={'draft': [('readonly', False)]}),
        'state': fields.selection([('cancel', 'Cancelled'),('draft', 'Draft'),('confirmed', 'Confirmed'),('exception', 'Exception'),('done', 'Done')], 'Status', required=True, readonly=True,
                help='* The \'Draft\' status is set when the related contract in draft status. \
                    \n* The \'Confirmed\' status is set when the related contract is confirmed. \
                    \n* The \'Exception\' status is set when the related contract is set as exception. \
                    \n* The \'Done\' status is set when the contract line has been picked. \
                    \n* The \'Cancelled\' status is set when a user cancel the contract related.'),
        'order_partner_id': fields.related('contract_id', 'partner_id', type='many2one', relation='res.partner', store=True, string='Customer'),
        'salesman_id':fields.related('contract_id', 'user_id', type='many2one', relation='res.users', store=True, string='Salesperson'),
        'company_id': fields.related('contract_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
    }
    _order = 'contract_id desc, sequence, id'
    _defaults = {
        'product_uom' : _get_uom_id,
        'discount': 0.0,
        'product_uom_qty': 1,
        'product_uos_qty': 1,
        'sequence': 10,
        'state': 'draft',
        'type': 'make_to_stock',
        'price_unit': 0.0,
    }

    def _get_line_qty(self, cr, uid, line, context=None):
        #if (line.contract_id.invoice_quantity=='order'):
        #    if line.product_uos:
        #        return line.product_uos_qty or 0.0
        return line.product_uom_qty

    def _get_line_uom(self, cr, uid, line, context=None):
        #if (line.contract_id.invoice_quantity=='order'):
        #    if line.product_uos:
        #        return line.product_uos.id
        return line.product_uom.id

    def _prepare_contract_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        """Prepare the dict of values to create the new invoice line for a
           contract line. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: sale.order.line record to invoice
           :param int account_id: optional ID of a G/L account to force
               (this is used for returning products including service)
           :return: dict of values to create() the invoice line
        """
        res = {}
        #logging.warning('line : %s' % line.invoiced)
        #if not line.invoiced:
        if not account_id:
            if line.product_id:
                account_id = line.product_id.property_account_income.id
                if not account_id:
                    account_id = line.product_id.categ_id.property_account_income_categ.id
                if not account_id:
                    raise osv.except_osv(_('Error!'),
                            _('Please define income account for this product: "%s" (id:%d).') % \
                                (line.product_id.name, line.product_id.id,))
            else:
                prop = self.pool.get('ir.property').get(cr, uid,
                        'property_account_income_categ', 'product.category',
                        context=context)
                account_id = prop and prop.id or False
        uosqty = self._get_line_qty(cr, uid, line, context=context)
        uos_id = self._get_line_uom(cr, uid, line, context=context)
        pu = 0.0
        if uosqty:
            pu = round(line.price_unit * line.product_uom_qty / uosqty,
                    self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
        fpos = line.contract_id.fiscal_position or False
        account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
        if not account_id:
            raise osv.except_osv(_('Error!'),
                        _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
        res = {
            'name': line.name,
            'sequence': line.sequence,
            'origin': line.contract_id.name,
            'account_id': account_id,
            'price_unit': pu,
            'quantity': uosqty,
            'discount': line.discount,
            'uos_id': uos_id,
            'product_id': line.product_id.id or False,
            'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
            'account_analytic_id': line.contract_id.analytic_account_id and line.contract_id.analytic_account_id.id or False,
        }

        return res

    def invoice_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        create_ids = []
        sales = set()
        for line in self.browse(cr, uid, ids, context=context):
            vals = self._prepare_contract_line_invoice_line(cr, uid, line, False, context)
            if vals:
                inv_id = self.pool.get('account.invoice.line').create(cr, uid, vals, context=context)
                self.write(cr, uid, [line.id], {'invoice_lines': [(4, inv_id)]}, context=context)
                sales.add(line.contract_id.id)
                create_ids.append(inv_id)
        # Trigger workflow events
        #wf_service = netsvc.LocalService("workflow")
        #for sale_id in sales:
        #    wf_service.trg_write(uid, 'sale.order', sale_id, cr)
        return create_ids

    def button_cancel(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if line.invoiced:
                raise osv.except_osv(_('Invalid Action!'), _('You cannot cancel a contract line that has already been invoiced.'))
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def button_confirm(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'confirmed'})

    def button_done(self, cr, uid, ids, context=None):
        #wf_service = netsvc.LocalService("workflow")
        res = self.write(cr, uid, ids, {'state': 'done'})
        #for line in self.browse(cr, uid, ids, context=context):
        #    wf_service.trg_write(uid, 'sale.order', line.order_id.id, cr)
        return res

    def uos_change(self, cr, uid, ids, product_uos, product_uos_qty=0, product_id=None):
        product_obj = self.pool.get('product.product')
        if not product_id:
            return {'value': {'product_uom': product_uos,
                'product_uom_qty': product_uos_qty}, 'domain': {}}

        product = product_obj.browse(cr, uid, product_id)
        value = {
            'product_uom': product.uom_id.id,
        }
        # FIXME must depend on uos/uom of the product and not only of the coeff.
        try:
            value.update({
                'product_uom_qty': product_uos_qty / product.uos_coeff,
                'th_weight': product_uos_qty / product.uos_coeff * product.weight
            })
        except ZeroDivisionError:
            pass
        return {'value': value}

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'state': 'draft',  'invoice_lines': []})
        return super(integc_hr_partner_contract_line, self).copy_data(cr, uid, id, default, context=context)

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        lang = lang or context.get('lang',False)
        if not  partner_id:
            raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
        warning = {}
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        context = {'lang': lang, 'partner_id': partner_id}
        if partner_id:
            lang = partner_obj.browse(cr, uid, partner_id).lang
        context_partner = {'lang': lang, 'partner_id': partner_id}

        if not product:
            return {'value': {'th_weight': 0,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date:
            date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False
        fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position) or False
        if update_tax: #The quantity only have changed
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
            if product_obj.description_sale:
                result['name'] += '\n'+product_obj.description_sale
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
        # get unit price

        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, {
                        'uom': uom or result.get('product_uom'),
                        'date': date,
                        })[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'price_unit': price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}

    def product_uom_change(self, cursor, user, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date=False, context=None):
        context = context or {}
        lang = lang or ('lang' in context and context['lang'])
        if not uom:
            return {'value': {'price_unit': 0.0, 'product_uom' : uom or False}}
        return self.product_id_change(cursor, user, ids, pricelist, product,
                qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name,
                partner_id=partner_id, lang=lang, update_tax=update_tax,
                date=date, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        """Allows to delete contract lines in draft,cancel states"""
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ['draft', 'cancel']:
                raise osv.except_osv(_('Invalid Action!'), _('Cannot delete a contract line which is in state \'%s\'.') %(rec.state,))
        return super(integc_hr_partner_contract_line, self).unlink(cr, uid, ids, context=context)

integc_hr_partner_contract_line()
