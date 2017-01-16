#-*- coding:utf-8 -*-

#Author: yenke

from openerp.report import report_sxw
from openerp.tools import amount_to_text_en
import logging
import time
from datetime import datetime
from dateutil import relativedelta


def format_amount(s, sep=' '):
    if len(s) <= 3:
        return s
    else:
        return format_amount(s[:-3]) + sep + s[-3:]


class payslip_run_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(payslip_run_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            #'get_payslip': self.get_payslip,
            #'get_payslip_lines': self.get_payslip_lines,
            'get_total_by_rule_category': self.get_total_by_rule_category,
            'get_payslip_amount_by_rule_code': self.get_payslip_amount_by_rule_code,
            'get_total_amount_by_category': self.get_total_amount_by_category,
            'get_total_payslip_amount_by_rule_code': self.get_total_payslip_amount_by_rule_code,
            'format_amount': format_amount

        })


    def get_payslip(self, obj):
        payslip = self.pool.get('hr.payslip')
        res = []
        ids = []
        for id in range(len(obj)):
            ids.append(obj[id].id)
        if ids:
            res = payslip.browse(self.cr, self.uid, ids)
        return res

    def get_payslip_amount_by_rule_code(self, obj, code):
        res = 0
        payslip_line = self.pool.get('hr.payslip.line')
        line_ids = payslip_line.search(self.cr, self.uid, [('slip_id', '=', obj.id),('code', '=', code )])
        for line in payslip_line.browse(self.cr, self.uid, line_ids):
            res += line.total
        return res

    def get_total_payslip_amount_by_rule_code(self, objects, code):
        res = 0
        for obj in objects:
            res += self.get_payslip_amount_by_rule_code(obj, code)
        return res

    def get_payslip_lines(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for id in range(len(obj)):
            if obj[id].appears_on_payslip == True:
                ids.append(obj[id].id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res

    def get_total_by_rule_category(self, obj, code):
        payslip_line = self.pool.get('hr.payslip.line')
        rule_cate_obj = self.pool.get('hr.salary.rule.category')

        cate_ids = rule_cate_obj.search(self.cr, self.uid, [('code', '=', code)])

        category_total = 0
        if cate_ids:
            line_ids = payslip_line.search(self.cr, self.uid, [('slip_id', '=', obj.id),('category_id.id', '=', cate_ids[0] )])
            for line in payslip_line.browse(self.cr, self.uid, line_ids):
                category_total += line.total
        return category_total

    def get_total_amount_by_category(self, objects, code):
        res = 0
        for obj in objects:
            res += self.get_total_by_rule_category(obj, code)
        return res

report_sxw.report_sxw('report.payslip.run', 'hr.payslip.run', 'integc/hr/report/report_payslip_run.rml', parser=payslip_run_report)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
