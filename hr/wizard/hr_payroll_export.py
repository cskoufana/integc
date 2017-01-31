#-*- coding: utf-8 -*-
#__author__ = 'yenke'
import base64


import time
from datetime import datetime
from dateutil import relativedelta
from openerp import SUPERUSER_ID, tools
from openerp.osv import fields, osv


class hr_payroll_export(osv.osv_memory):
    _name = 'hr.payroll.export'
    _description = 'Payroll export to DIPE format'
    _columns = {
        'name': fields.char('File name', readonly=True),
        'data': fields.binary('File', readonly=True),
        'state': fields.selection([('confirm', 'confirm'),     # confirm choice
                                       ('get', 'get')])        # get the file
    }
    _defaults = {
        'state': 'confirm',
    }

    def get_total_by_rule_category(self, cr, uid, slip_id, code):
        payslip_line = self.pool.get('hr.payslip.line')
        rule_cate_obj = self.pool.get('hr.salary.rule.category')

        cate_ids = rule_cate_obj.search(cr, uid, [('code', '=', code)])
        category_total = 0
        if cate_ids:
            line_ids = payslip_line.search(cr, uid, [('slip_id', '=', slip_id),('category_id.id', '=', cate_ids[0] )])
            for line in payslip_line.browse(cr, uid, line_ids):
                category_total += line.total
        return category_total

    def get_payslip_amount_by_rule_code(self, cr, uid, slip_id, code):
        res = 0
        payslip_line = self.pool.get('hr.payslip.line')
        line_ids = payslip_line.search(cr, uid, [('slip_id', '=', slip_id),('code', '=', code )])
        for line in payslip_line.browse(cr, uid, line_ids):
            res += line.total
        return res

    def act_getfile(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids, context=context)[0]
        payslip_obj = self.pool.get('hr.payslip.run')
        content = '\n\n\n'
        i = 1
        month = year = ''
        for record in payslip_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            col_1 = 'C0400000'+' '*15
            month = str(record.date_start)[:7][5:]
            year = str(record.date_start)[:4]
            code = '3210103747H1'
            i = 0
            for slip in record.slip_ids:
                i += 1
                ssnid = str(slip.employee_id.ssnid).replace('-', '') if slip.employee_id.ssnid else ''
                col_2 = month + code + year + (' ' * (11 - len(ssnid)) + ssnid) + '30'
                brut = int(self.get_total_by_rule_category(cr, uid, slip.id, 'BRUT'))
                col_3 = ' ' * (11 - len(str(brut))) + str(brut)
                elt_exp = int(self.get_payslip_amount_by_rule_code(cr, uid, slip.id, 'INDMTRANSP'))
                col_4 = ' ' * (10 - len(str(elt_exp))) + str(elt_exp)
                brut_taxable = int(self.get_total_by_rule_category(cr, uid, slip.id, 'BRUT_TAXABLE'))
                col_5 = ' ' * (10 - len(str(brut_taxable))) + str(brut_taxable)
                brut_cot = int(self.get_total_by_rule_category(cr, uid, slip.id, 'BRUT_COTISABLE'))
                col_6 = ' ' * (10 - len(str(brut_cot))) + str(brut_cot)
                brut_cot_pla = 750000 if brut_cot > 750000 else brut_cot
                col_7 = ' ' * (10 - len(str(brut_cot_pla))) + str(brut_cot_pla)
                irpp = int(self.get_payslip_amount_by_rule_code(cr, uid, slip.id, 'IRPP'))
                str_irpp = str(irpp) + '0' * (7 - len(str(i))) + str(i)
                col_8 = ' ' * (16 - len(str(str_irpp))) + str(str_irpp)
                col_9 = ' ' * (14 - len(slip.employee_id.otherid)) + slip.employee_id.otherid
                col_10 = ' ' * (60 - len(slip.employee_id.name)) + slip.employee_id.name
                content += '%s%s%s%s%s%s%s%s%s%s\n' % (col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8, col_9, col_10, )

        out = base64.encodestring(content)
        name = 'dipe_%s_%s.txt' % (month, year)
        this.write({'state': 'get', 'data': out, 'name': name })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.export',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': this.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
