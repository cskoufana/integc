#-*- coding:utf-8 -*-

from openerp.report import report_sxw
from openerp.tools import amount_to_text_en
import logging

class transfer_order_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(transfer_order_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
        })



report_sxw.report_sxw('report.transfer.order', 'account.voucher', 'integc/account/report/transfer_report.rml', parser=transfer_order_report)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
