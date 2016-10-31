# -*- coding: utf-8 -*-
#__author__ = 'yenke'


from openerp.osv import fields, osv
from openerp.tools.translate import _


class res_partner_bank(osv.osv):
    """
    Bank Account
    """
    _name = "res.partner.bank"
    _inherit = "res.partner.bank"
    _columns = {
        'pos': fields.char('Point Of Sale', size=64, required=True),
        'key': fields.char('Key', size=64, required=True),
    }
res_partner_bank()