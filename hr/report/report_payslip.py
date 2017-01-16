#-*- coding:utf-8 -*-

#__author__ = 'yenke'


from openerp.report import report_sxw
from openerp.tools import amount_to_text_en
import os
import logging


def format_amount(s, sep=' '):
    if len(s) <= 3:
        return s
    else:
        return format_amount(s[:-3]) + sep + s[-3:]

class payslip_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(payslip_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_payslip_lines': self.get_payslip_lines,
            'get_total_by_rule_category': self.get_total_by_rule_category,
            'format_amount': format_amount
        })

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
        #logging.warning(code)
        if cate_ids:
            line_ids = payslip_line.search(self.cr, self.uid, [('slip_id', '=', obj.id),('category_id.id', '=', cate_ids[0] )])
            for line in payslip_line.browse(self.cr, self.uid, line_ids):
                #logging.warning('%s - %s' % (code, line.total))
                category_total += line.total
        return category_total

report_sxw.report_sxw('report.integc.payslip', 'hr.payslip', 'integc/hr/report/report_payslip.rml', parser=payslip_report)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
