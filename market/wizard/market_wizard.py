#__author__ = 'yenke'

import time
from datetime import datetime
from dateutil import relativedelta
from openerp import SUPERUSER_ID, tools
from openerp.osv import fields, osv

class market_invoice(osv.osv_memory):
    _name = 'market.invoice'
    _columns = {
        'market_id': fields.many2one('integc.market', 'Market', readonly=True),
        'contract_id': fields.many2one('integc.market.contract', 'Contract', required=True,
                                       domain="[('market_id', '=', market_id), ('state', '=', 'open')]"),
        'contract_type': fields.related('contract_id', 'type', type='char', string='Type'),
        'amount_total': fields.related('contract_id', 'amount_total', type='float', string='Amount total'),
        'expected_count': fields.related('contract_id', 'expected_count', type='float', string='Expected count'),
        'count_paid': fields.related('contract_id', 'count_paid', type='float', string='Count paid'),
        'balance': fields.related('contract_id', 'balance', type='float', string='Unexpected count'),
    }

    def onchange_contract(self, cr, uid, ids, contract_id, context=None):
        res = {
            'value': {
                'contract_type': False,
                'amount_total': 0.0,
                'expected_account': 0.0,
                'account_paid': 0.0,
                'balance': 0.0,
            }
        }
        if contract_id:
            contract = self.pool.get('integc.market.contract').browse(cr, uid, contract_id, context=context)
            if contract:
                res['value']['contract_type'] = contract.type
                res['value']['amount_total'] = contract.amount_total
                res['value']['expected_count'] = contract.expected_count
                res['value']['count_paid'] = contract.count_paid
                res['value']['balance'] = contract.balance
        return res

    def default_get(self, cr, uid, fields, context=None):
        res = super(market_invoice, self).default_get(cr, uid, fields, context=context)
        active_id = context.get('active_id', False)
        res['market_id'] = active_id,
        return res

    def action_validate(self, cr, uid, ids, context=None):
        contract_obj = self.pool.get('integc.market.contract')
        res = {}
        for wizard in self.browse(cr, uid, ids, context):
            res = contract_obj.create_invoice(cr, uid, [wizard.contract_id.id], context=context)
            #res['type'] = 'ir.actions.act_window_close'
            return res
            #return {'type': 'ir.actions.act_window_close'}