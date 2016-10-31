# -*- coding: utf-8 -*-
#__author__ = 'yenke'


from openerp.osv import fields, osv
import time
from datetime import datetime
from openerp import tools
from openerp.osv.orm import except_orm
from openerp.tools.translate import _


class account_invoice(osv.osv):
    """
    Account invoice
    """
    _name = 'account.invoice'
    _inherit = 'account.invoice'
    _columns = {
        'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            ('open0','Project leader'),
            ('open1', 'Engineer market'),
            ('open2', 'Service manager'),
            ('open3', 'Project manager'),
            ('open4', 'MINMAP'),
            ('open5', 'Pending payment'),
            ('paid','Paid'),
            ('cancel','Cancelled'),

            ],'Status', select=True, readonly=True, track_visibility='onchange',
            help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed Invoice. \
            \n* The \'Pro-forma\' when invoice is in Pro-forma status,invoice does not have an invoice number. \
            \n* The \'Open\' status is used when user create invoice,a invoice number is generated.Its in open status till user does not pay invoice. \
            \n* The \'Paid\' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled. \
            \n* The \'Cancelled\' status is used when user cancel invoice.'),
        #'stage_ids': fields.many2many('integc.account.invoice.stage', 'integc_account_invoice_stage_rel','invoice_id', 'stage_id', 'Stages'),
        'stage_ids': fields.one2many('integc.account.invoice.stage', 'invoice_id', 'Stages'),
    }

    def invoice_validate(self, cr, uid, ids, context=None):
        contract_name, balance = self.pool.get('integc.hr.partner.contract').get_contract_balance(cr, uid, ids[0], context=None)
        if not contract_name:
            contract_name, balance = self.pool.get('integc.market.contract').get_contract_balance(cr, uid, ids[0], context=None)
        if contract_name:
            for record in self.browse(cr, uid, ids, context=context):
                if record.amount_total > balance:
                    raise osv.except_osv(_('Operation not allowed!'), _('You can''t not validate that invoice with the amount %s.\n'
                                                                        'The contract %s related to that invoice has balance %s' % (record.amount_total, contract_name, balance)))
        for record in self.browse(cr, uid, ids, context=context):
            for stage in record.stage_ids:
                if stage.state == 'open0':
                    self.pool.get('integc.account.invoice.stage').write(cr, uid, stage.id, {'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
            if record.type == 'out_invoice':
                return self.write(cr, uid, ids, {'state': 'open0'}, context=context)
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def action_open1(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            for stage in record.stage_ids:
                if stage.state == 'open0':
                    self.pool.get('integc.account.invoice.stage').write(cr, uid, stage.id, {'date_end': time.strftime('%Y-%m-%d %H:%M:%S')})
                if stage.state == 'open1':
                    self.pool.get('integc.account.invoice.stage').write(cr, uid, stage.id, {'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return self.write(cr, uid, ids, {'state': 'open1'}, context=context)

    def action_open2(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            for stage in record.stage_ids:
                if stage.state == 'open1':
                    self.pool.get('integc.account.invoice.stage').write(cr, uid, stage.id, {'date_end': time.strftime('%Y-%m-%d %H:%M:%S')})
                if stage.state == 'open2':
                    self.pool.get('integc.account.invoice.stage').write(cr, uid, stage.id, {'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return self.write(cr, uid, ids, {'state': 'open2'}, context=context)

    def action_open3(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            for stage in record.stage_ids:
                if stage.state == 'open2':
                    self.pool.get('integc.account.invoice.stage').write(cr, uid, stage.id, {'date_end': time.strftime('%Y-%m-%d %H:%M:%S')})
                if stage.state == 'open3':
                    self.pool.get('integc.account.invoice.stage').write(cr, uid, stage.id, {'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return self.write(cr, uid, ids, {'state': 'open3'}, context=context)

    def action_open4(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            for stage in record.stage_ids:
                if stage.state == 'open3':
                    self.pool.get('integc.account.invoice.stage').write(cr, uid, stage.id, {'date_end': time.strftime('%Y-%m-%d %H:%M:%S')})
                if stage.state == 'open4':
                    self.pool.get('integc.account.invoice.stage').write(cr, uid, stage.id, {'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return self.write(cr, uid, ids, {'state': 'open4'}, context=context)

    def action_open5(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            for stage in record.stage_ids:
                if stage.state == 'open4':
                    self.pool.get('integc.account.invoice.stage').write(cr, uid, stage.id, {'date_end': time.strftime('%Y-%m-%d %H:%M:%S')})
        return self.write(cr, uid, ids, {'state': 'open5'}, context=context)

    def create(self, cr, uid, values, context=None):
        ids = super(account_invoice, self).create(cr, uid, values, context=context)
        if not 'type' in values or ('type' in values and values['type'] == 'out_invoice'):
            self.create_default_stage(cr, uid, ids, context=context)
        return ids

    def create_default_stage(self, cr, uid, ids, context=None):
        stage_obj = self.pool.get('integc.account.invoice.stage')
        values = {
            'name': 'Project leader',
            'state': 'open0',
            'sequence': 1,
            'default': 1,
            'delay': 2,
            'invoice_id': ids,
        }
        stage_obj.create(cr, uid, values, context=context)
        values['name'] = 'Engineer market'
        values['state'] = 'open1'
        values['sequence'] = 2
        stage_obj.create(cr, uid, values, context=context)
        values['name'] = 'Service manager'
        values['state'] = 'open2'
        values['sequence'] = 3
        stage_obj.create(cr, uid, values, context=context)
        values['name'] = 'Project Manager'
        values['state'] = 'open3'
        values['sequence'] = 4
        stage_obj.create(cr, uid, values, context=context)
        values['name'] = 'MINMAP'
        values['state'] = 'open4'
        values['sequence'] = 5
        stage_obj.create(cr, uid, values, context=context)
        return True


    def get_critical_delay(self, cr, uid, context=None):
        invoice_ids = self.search(cr, uid, [('state', 'not in', ('draft','cancel','paid')), ('type', '=', 'out_invoice')], context=context)
        for record in self.browse(cr, uid, invoice_ids, context=context):
            for stage in record.stage_ids:
                if stage.state == record.state:
                    #compute delay
                    delay = ((datetime.strptime(time.strftime('%Y-%m-%d'),'%Y-%m-%d') - datetime.strptime(stage.date_start, '%Y-%m-%d')).days)
                    if delay >= stage.delay:
                        self.message_post(cr, uid, [record.id], body=_('Step %s of the invoice %s has exceeded the time limit.') % (stage.name, record.name))
        return True

    def scheduler_stage_delay(self, cr, uid, context=None):
        self.get_critical_delay(cr, uid, context=context)
        return True

account_invoice()


class integc_account_invoice_stage(osv.osv):
    _name = 'integc.account.invoice.stage'
    _description = 'Customer invoice stage'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence'),
        'default': fields.boolean('Default for invoices'),
        'delay': fields.integer('Delay (Days)'),
        'state': fields.selection([
            ('open0','Project leader'),
            ('open1', 'Engineer market'),
            ('open2', 'Service manager'),
            ('open3', 'Project manager'),
            ('open4', 'MINMAP'),
        ], string='State'),
        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
        'date_start': fields.datetime('Date start', readonly=True),
        'date_end': fields.datetime('Date end', readonly=True),
    }
    _order = 'sequence'
integc_account_invoice_stage()