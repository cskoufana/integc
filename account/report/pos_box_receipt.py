#-*- coding:utf-8 -*-
#__author__ = 'yenke'

from openerp.report import report_sxw
from openerp.tools import amount_to_text_en
import time


def format_amount(s, sep=' '):
    if len(s) <= 3:
        return s
    else:
        return format_amount(s[:-3]) + sep + s[-3:]


class pos_box_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(pos_box_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'format_amount': format_amount,
        })

report_sxw.report_sxw('report.pos.box', 'account.bank.statement.line', 'integc/account/report/receipt.rml', parser=pos_box_report)