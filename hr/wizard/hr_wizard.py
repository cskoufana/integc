#__author__ = 'yenke'

import time
from datetime import datetime
from dateutil import relativedelta
from openerp import SUPERUSER_ID, tools
from openerp.osv import fields, osv


class partner_contract(osv.osv_memory):
    _name = 'partner.contract'
    _columns = {
        'decision': fields.selection([
            ('done', 'Complete'),
            ('cancel', 'Cancel')
        ], string="Decision", required=True),
        'date': fields.date('Date'),
        'note': fields.text('Notes')
    }

    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def action_validate(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context)
        partner_contract_obj = self.pool.get('integc.hr.partner.contract')
        if wizard.decision == 'done':
            partner_contract_obj.action_complete(cr, uid, context.get('active_ids', []), context)
        else:
            partner_contract_obj.action_cancel(cr, uid, context.get('active_ids', []), context)
        #partner_contract_obj.write(cr, uid, context.get('active_ids', []), {
        #    'state': wizard.decision,
        #}, context=context)
        return {'type': 'ir.actions.act_window_close'}

partner_contract()


class integc_hr_contract(osv.osv_memory):
    _name = 'integc.hr.contract'
    _columns = {
        'decision': fields.selection([
            ('done', 'Complete'),
            ('cancel', 'Cancel')
        ], string="Decision", required=True),
        'date': fields.date('Date'),
        'note': fields.text('Notes')
    }

    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def action_validate(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context)
        hr_contract_obj = self.pool.get('hr.contract')
        if wizard.decision == 'done':
            hr_contract_obj.action_done(cr, uid, context.get('active_ids', []), context)
        else:
            hr_contract_obj.action_cancel(cr, uid, context.get('active_ids', []), context)
        #partner_contract_obj.write(cr, uid, context.get('active_ids', []), {
        #    'state': wizard.decision,
        #}, context=context)
        return {'type': 'ir.actions.act_window_close'}

integc_hr_contract()
