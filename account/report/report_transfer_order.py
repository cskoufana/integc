#-*- coding:utf-8 -*-

from openerp.report import report_sxw
from openerp.tools import amount_to_text_en
import logging
import utility

class transfer_order_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(transfer_order_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_bank_account_by_partner': self.get_bank_account_by_partner,
            'get_amount_letter': self.get_amount_letter,
            'get_total_amount_by_partner': self.get_total_amount_by_partner,
            'get_partner_list': self.get_partner_list,
        })

    def get_bank_account_by_partner(self, obj):
        res = []
        employee_obj = self.pool.get('hr.employee')
        employee_ids = employee_obj.search(self.cr, self.uid, [('address_home_id', '=', obj)])
        if employee_ids:
            for record in employee_obj.browse(self.cr, self.uid, employee_ids):
                res = record.bank_account_id
                #res = self.pool.get('res.partner.bank').browse(self.cr, self.uid, record.bank_account_id.id)
        return res

    def get_total_amount_by_partner(self, obj, partner):
        res = 0.0
        voucher_obj = self.pool.get('account.voucher')
        for record in voucher_obj.browse(self.cr, self.uid, [obj.id]):
            for line in record.line_ids:
                if line.partner_id.id == partner.id:
                    if line.type == 'cr':
                        res -= line.amount
                    elif line.type == 'dr':
                        res += line.amount
        return res

    def get_partner_list(self, obj):
        res = []
        voucher_obj = self.pool.get('account.voucher')
        for record in voucher_obj.browse(self.cr, self.uid, [obj.id]):
            if record.partner_id:
                res.append(record.partner_id)
            for partner in record.partner_ids:
                res.append(partner)
        return res


    def get_amount_letter(self, amount):
        logging.warning(amount)
        return str(utility.trad(float(amount))).upper()








report_sxw.report_sxw('report.transfer.order', 'account.voucher', 'integc/account/report/transfer_report.rml', parser=transfer_order_report)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
