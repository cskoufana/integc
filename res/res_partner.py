# -*- coding: utf-8 -*-
#__author__ = 'yenke'

from openerp.osv import fields, osv


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _name = 'res.partner'
    _description = 'Partner'
    _columns = {
        'niu': fields.char('NIU', size=64),
        #'ssnid': fields.char('Social Security Number', size=64),
        #'ssregime': fields.char('Social Security Regime', size=64),
    }

res_partner()

