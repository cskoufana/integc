#-*- coding:utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.report import report_sxw
from openerp.tools import amount_to_text_en
import logging
import time
from datetime import datetime
from dateutil import relativedelta

class integc_payslip_journal_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(integc_payslip_journal_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_payslip_lines': self.get_payslip_lines,
            'get_total_by_rule_category': self.get_total_by_rule_category,
            'get_payslip_amount_by_rule_code': self.get_payslip_amount_by_rule_code,
            'get_total_amount_by_category': self.get_total_amount_by_category,
            'get_total_payslip_amount_by_rule_code': self.get_total_payslip_amount_by_rule_code

        })

    #def set_context(self, objects, data, ids, report_type=None):
    #    #self.date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))
    #    #self.date_to = data['form'].get('date_to', str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    #    logging.warning(data)
    #    #logging.warning(objects)
    #    return super(integc_payslip_journal_report, self).set_context(objects, data, ids, report_type=report_type)

    def get_payslip_amount_by_rule_code(self, obj, code):
        res = 0
        #logging.warning('%s - %s' % (obj, code))
        payslip_line = self.pool.get('hr.payslip.line')
        line_ids = payslip_line.search(self.cr, self.uid, [('slip_id', '=', obj.id),('code', '=', code )])
        for line in payslip_line.browse(self.cr, self.uid, line_ids):
            #logging.warning(line)
            res += line.total
        return res

    def get_total_payslip_amount_by_rule_code(self, object, code):
        res = 0
        for obj in object:
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
        #logging.warning(code)
        if cate_ids:
            line_ids = payslip_line.search(self.cr, self.uid, [('slip_id', '=', obj.id),('category_id.id', '=', cate_ids[0] )])
            for line in payslip_line.browse(self.cr, self.uid, line_ids):
                #logging.warning('%s - %s' % (code, line.total))
                category_total += line.total

        return category_total

    def get_total_amount_by_category(self, object, code):
        res = 0
        for obj in object:
            res += self.get_total_by_rule_category(obj, code)
        return res

report_sxw.report_sxw('report.integc.payslip.journal', 'hr.payslip', 'integc/hr/report/report_journal.rml', parser=integc_payslip_journal_report)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
