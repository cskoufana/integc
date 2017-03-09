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
_logger = logging.getLogger(__name__)


class integc_need(osv.osv):

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        #cur_obj = self.pool.get('res.currency')
        res = {}
        for need in self.browse(cr, uid, ids, context=context):
            res[need.id] = {
                'amount_total': 0.0,
            }
            val = 0.0
            #cur = need.pricelist_id.currency_id
            for line in need.need_line:
                val += line.price_subtotal
            #res[need.id]['amount_total'] = cur_obj.round(cr, uid, cur, val)
            res[need.id]['amount_total'] = val
            #logging.info(res)
        return res

    def _get_need(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('integc.need.line').browse(cr, uid, ids, context=context):
            result[line.need_id.id] = True
        return result.keys()

    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        return company_id

    def _purchase_order_exists(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for need in self.browse(cursor, user, ids, context=context):
            res[need.id] = False
            if need.purchase_order_id:
                res[need.id] = True
        return res


    _name = 'integc.need'
    _description = 'Needs'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _track = {
        'type': {
        },
        'state': {
            'integc.mt_need_validated': lambda self, cr, uid, obj, ctx=None: obj['state'] in ('validation_head_department', 'validation_director', 'validation_daf', 'validation_manager', 'payment'),
            'intgec.mt_need_paid': lambda self, cr, uid, obj, ctx=None: obj.state == 'done',
            'intgec.mt_need_cancel': lambda self, cr, uid, obj, ctx=None: obj.state == 'cancel',
        },
    }
    _columns = {
        'name': fields.char('Reference'),
        'note': fields.text('Notes'),
        #'employee_id': fields.many2one('hr.employee', 'Employee'),
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Supplier'),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic account'),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('validation_head_department', 'Validation Department Head'),
            ('validation_director', 'Validation Director'),
            ('validation_daf', 'Validation DAF'),
            ('validation_manager', 'Validation Manager'),
            ('payment', 'Payment'),
            ('done', 'Done')
        ], 'Status', readonly=True, track_visibility='onchange'),
        'date': fields.datetime('Date'),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', readonly=True),
        'currency_id': fields.related('pricelist_id', 'currency_id', type="many2one", relation="res.currency", string="Currency", readonly=True, required=False),
        'need_line': fields.one2many('integc.need.line', 'need_id', 'Need Lines'),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'integc.need': (lambda self, cr, uid, ids, c={}: ids, ['need_line'], 10),
                'integc.need.line': (_get_need, ['price_unit', 'product_uom_qty'], 10),
            },
            multi='sums', help="The total amount."),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'purchase_order_id': fields.many2one('purchase.order', 'Purchase Order'),
        'purchase_order_exists': fields.function(_purchase_order_exists, string='purchased', type='boolean'),

    }
    _order = 'id desc'
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': 'draft',
        'user_id': lambda obj, cr, uid, context: uid,
        'company_id': _get_default_company,
    }

    def onchange_pricelist_id(self, cr, uid, ids, pricelist_id, need_lines, context=None):
        context = context or {}
        if not pricelist_id:
            return {}
        value = {
            'currency_id': self.pool.get('product.pricelist').browse(cr, uid, pricelist_id, context=context).currency_id.id
        }
        return {'value': value}

    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        val = {}
        if part:
            part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
            pricelist = part and part.property_product_pricelist and part.property_product_pricelist.id or False
            val['pricelist_id'] = pricelist
        return {'value': val}

    def create(self, cr, uid, values, context=None):
        values['name'] = self.pool.get('ir.sequence').get(cr, uid, 'integc.need')
        return super(integc_need, self).create(cr, uid, values, context=context)

    def action_view_purchase_order(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'purchase', 'purchase_form_action')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]

        for need in self.browse(cr, uid, ids, context=context):
            res = mod_obj.get_object_reference(cr, uid, 'purchase', 'purchase_order_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = need.purchase_order_id and need.purchase_order_id.id or False
        return result

    def _prepare_purchase_line(self, cr, uid, order_id, line, account_id=False, context=None):
        res = {}
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
        if not account_id:
            raise osv.except_osv(_('Error!'),
                        _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
        res = {
            'name': line.name,
            'sequence': line.sequence,
            'origin': line.need_id.name,
            'account_id': account_id,
            'price_unit': 0.0,
            'quantity': line.product_uom_qty,
            'product_id': line.product_id.id or False,
            'account_analytic_id': line.need_id.analytic_account_id and line.need_id.analytic_account_id.id or False,
            'order_id': order_id,
            'date_planned': time.strftime('%Y-%m-%d'),
        }
        return res

    def purchase_line_create(self, cr, uid, ids, order_id, context=None):
        if context is None:
            context = {}
        create_ids = []
        for need in self.browse(cr, uid, ids, context=context):
            for line in need.need_line:
                vals = self._prepare_purchase_line(cr, uid, order_id, line, False, context)
                if vals:
                    inv_id = self.pool.get('purchase.order.line').create(cr, uid, vals, context=context)
                    create_ids.append(inv_id)
        return create_ids

    def create_purchase(self, cr, uid, ids, context=None):
        purchase_obj = self.pool.get('purchase.order')

        for record in self.browse(cr, uid, ids, context=context):
            values = {
                'origin': record.name,
                'partner_id': record.partner_id.id if record.partner_id else None,
                'location_id': record.partner_id.property_stock_supplier.id,
                'pricelist_id': record.partner_id.property_product_pricelist_purchase.id,
            }
        purchase_id = purchase_obj.create(cr, uid, values, context=context)
        created_lines = self.purchase_line_create(cr, uid, ids, purchase_id, context=context)
        purchase_obj.write(cr, uid, purchase_id, {'order_line': [(6, 0, created_lines)]}, context=context)
        self.write(cr, uid, ids, {'purchase_order_id': purchase_id}, context=context)

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'purchase', 'purchase_form_action')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        res_ = mod_obj.get_object_reference(cr, uid, 'purchase', 'purchase_order_form')
        result['views'] = [(res_ and res_[1] or False, 'form')]
        result['res_id'] = purchase_id or False
        return result

integc_need()


class integc_need_line(osv.osv):

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        #cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.price_unit * line.product_uom_qty
            #cur = line.need_id.pricelist_id.currency_id
            #res[line.id] = cur_obj.round(cr, uid, cur, price)
            res[line.id] = price
            #logging.info(res)
        return res


    def _get_uom_id(self, cr, uid, *args):
        try:
            proxy = self.pool.get('ir.model.data')
            result = proxy.get_object_reference(cr, uid, 'product', 'product_uom_unit')
            return result[1]
        except Exception as ex:
            return False


    _name = 'integc.need.line'
    _description = 'Need action line'
    _columns = {
        'name': fields.text('Description', required=True),
        'need_id': fields.many2one('integc.need', 'Need'),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price'), readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom_qty': fields.float('Quantity', digits_compute= dp.get_precision('Product UoS'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of contract lines."),
        'type': fields.selection([('make_to_stock', 'from stock'), ('make_to_order', 'on order')], 'Procurement Method', required=True, readonly=True, states={'draft': [('readonly', False)]},
         help="From stock: When needed, the product is taken from the stock or we wait for replenishment.\nOn order: When needed, the product is purchased or produced."),
        'product_uos_qty': fields.float('Quantity (UoS)' ,digits_compute= dp.get_precision('Product UoS'), readonly=True, states={'draft': [('readonly', False)]}),
        'product_uos': fields.many2one('product.uom', 'Product UoS'),
        'state': fields.selection([('cancel', 'Cancelled'),('draft', 'Draft'),('confirmed', 'Confirmed'),('exception', 'Exception'),('done', 'Done')], 'Status', required=True, readonly=True),
    }
    _order = 'need_id desc, sequence, id'
    _defaults = {
        'product_uom': _get_uom_id,
        'product_uom_qty': 1,
        'price_unit': 0.0,
        'sequence': 10,
        'state': 'draft',
        'type': 'make_to_stock',
    }

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        lang = lang or context.get('lang',False)
        if not  partner_id:
            raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a supplier in the sales form.'))
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

integc_need_line()
