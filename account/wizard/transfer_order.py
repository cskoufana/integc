#__author__ = 'yenke'
import base64
from openerp.osv import fields, osv
import time
from openerp.tools.translate import _

class transferOrder(osv.osv_memory):
    _name = 'transfer.order'
    _columns = {
        'name': fields.char('File Name', readonly=True),
        'data': fields.binary('File', readonly=True),
        'export_all': fields.boolean('Export all'),
        'state': fields.selection([('confirm', 'confirm'),     # confirm choice
                                       ('get', 'get')])        # get the file
    }
    _defaults = {
        'state': 'confirm',
        'export_all': False,
    }

    def get_total_amount_by_partner(self, cr, uid, obj, partner=None):
        res = 0.0
        if not partner:
            partner = obj.partner_id
        voucher_obj = self.pool.get('account.voucher')
        for record in voucher_obj.browse(cr, uid, [obj.id]):
            for line in record.line_ids:
                if line.partner_id.id == partner.id:
                    if line.type == 'cr':
                        res -= line.amount
                    elif line.type == 'dr':
                        res += line.amount
        return res

    def act_getfile(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids, context=context)[0]
        voucher_obj = self.pool.get('account.voucher')
        header = "NUMERO;NOMS ET PRENOMS;BANQUE;CODE BANQUE;CODE GUICHET;NUMERO DE COMPTE;CLE;MONTANT\n"
        content = header
        i = 1
        month = ''
        year = ''
        for record in voucher_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            month = str(record.date)[:7][5:]
            year = str(record.date)[:4]
            if record.partner_id:
                if this.export_all or (len(record.partner_id.bank_ids) > 0):
                    content += "%s;%s;%s;%s;%s;%s;%s;%s\n" % (++i, record.partner_id.name, record.partner_id.bank_ids and record.partner_id.bank_ids[0].bank.name or '', record.partner_id.bank_ids and record.partner_id.bank_ids[0].bank.bic or '', record.partner_id.bank_ids and record.partner_id.bank_ids[0].pos or '',record.partner_id.bank_ids and record.partner_id.bank_ids[0].acc_number or '', record.partner_id.bank_ids and record.partner_id.bank_ids[0].key or '', self.get_total_amount_by_partner(cr, uid, record))
            else:
                for partner in record.partner_ids:
                    if this.export_all or (len(partner.bank_ids) > 0):
                        content += "%s;%s;%s;%s;%s;%s;%s;%s\n" % (++i, partner.name, partner.bank_ids and partner.bank_ids[0].bank.name or '', partner.bank_ids and partner.bank_ids[0].bank.bic or '', partner.bank_ids and partner.bank_ids[0].pos or '', partner.bank_ids and partner.bank_ids[0].acc_number or '', partner.bank_ids and partner.bank_ids[0].key or '', self.get_total_amount_by_partner(cr, uid, record, partner))
        out = base64.encodestring(content)
        name = 'VIREMENT_SALAIRE_%s_%s.csv' % (month, year)
        this.write({ 'state': 'get', 'data': out, 'name': name })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'transfer.order',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': this.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
