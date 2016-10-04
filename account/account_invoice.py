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
            ('paid','Paid'),
            ('cancel','Cancelled'),
            ('approval1', 'Approval 1'),
            ('approval3', 'Approval 3'),
            ('approval4', 'Approval 4'),
            ('approval5', 'Approval 5'),
            ('approval6', 'Approval 6'),
            ],'Status', select=True, readonly=True, track_visibility='onchange',
            help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed Invoice. \
            \n* The \'Pro-forma\' when invoice is in Pro-forma status,invoice does not have an invoice number. \
            \n* The \'Open\' status is used when user create invoice,a invoice number is generated.Its in open status till user does not pay invoice. \
            \n* The \'Paid\' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled. \
            \n* The \'Cancelled\' status is used when user cancel invoice.'),
    }

    #def invoice_validate(self, cr, uid, ids, context=None):
    #    cr.execute('SELECT rel.contract_id FROM integc_hr_partner_contract_invoice_rel AS rel WHERE rel.invoice_id = %s' % ids[0])
    #    res = cr.fetchall()
    #    if res:
    #        for x in res:
    #            self.pool.get('integc.hr.partner.contract').write(cr, uid, [x[0]], {}, context)
    #    return self.write(cr, uid, ids, {'state':'open'}, context=context)
    #    #return super(account_invoice, self).invoice_validate(self, cr, uid, ids, context=context)

account_invoice()