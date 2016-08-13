#-*- coding: utf-8 -*-
#__author__ = 'yenke'

import time
from datetime import datetime
from dateutil import relativedelta
from openerp import SUPERUSER_ID, tools
from openerp.osv import fields, osv
import logging


class hr_payslip_journal(osv.osv_memory):
    _name = 'hr.payslip.journal'
    _description = 'Payslip journal'
    _columns = {
        'date_from': fields.date('Date From', required=True),
        'date_to': fields.date('Date To', required=True),
    }

    _defaults = {
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'date_to': lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
    }

    def print_report(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context)
        if wizard.date_to < wizard.date_from:
            raise osv.except_osv('Erreur', 'La date de fin doit etre superieure a la date de debut')
        model = 'hr.payslip',
        payslip_obj = self.pool.get('hr.payslip')
        payslip_ids = payslip_obj.search(cr, uid, [('date_from', '>=', wizard.date_from), ('date_to', '<=', wizard.date_to), ('state', '=', 'done')], context=context)
        user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        datas = {
            'ids': payslip_ids,
            'model': model,
            #'form': payslip_obj.read(cr, uid, payslip_ids, [], context=context)
            'form': {
                'date_from': wizard.date_from,
                'date_to': wizard.date_to,
                'company_name': user.company_id.name,
                'company_pob': user.company_id.zip or '',
                'company_niu': user.company_id.partner_id.niu or '',
                'company_phone': user.company_id.phone or '',
                'company_address': '%s %s' % (user.company_id.partner_id.street or '' ,user.company_id.partner_id.city or ''),
            }
        }
        #logging.warning(datas)
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'integc.payslip.journal',
            'datas': datas,
        }
hr_payslip_journal()
