# -*- coding: utf-8 -*-
#__author__ = 'yenke'



from openerp.osv import fields, osv
from dateutil import relativedelta
import time
from datetime import datetime
from datetime import timedelta
from openerp import tools
from openerp.osv.orm import except_orm
from openerp.tools.translate import _
from openerp.tools import config, float_compare
import logging
_logger = logging.getLogger(__name__)


def subtract_month(dt, month):
    ndt = dt
    for n in range(month):
        dt0 = ndt.replace(day=1)
        dt1 = dt0 - timedelta(days= 1)
        ndt = dt1.replace(day=1)
    return ndt.strftime('%Y-%m-%d')

class hr_employee(osv.osv):
    _name = 'hr.employee'
    _inherit = 'hr.employee'

    def _is_registered(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = record.ssnid if record.ssnid else False
        return res

    def _set_registered(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            this = self.browse(cr, uid, id, context=context)
            res = this.ssnid and True if this.ssnid else False
            self.write(cr, uid, id, {'is_registered': res})
            return res

    def _has_contract(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        contract_ids = self.pool.get('hr.contract').search(cr, uid, [('employee_id', 'in', ids), ('state', '=', 'progress')], context=context)
        res[ids[0]] = contract_ids and True or False
        return res

    def _set_contract(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            contract_ids = self.pool.get('hr.contract').search(cr, uid, [('employee_id', '=', id), ('state', '=', 'progress')], context=context)
            res = contract_ids and True or False
            self.write(cr, uid, id, {'has_contract': res})
            return res

    _columns = {
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'State'),
        #'country_id': fields.many2one('res.country', 'Country'),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'bank': fields.many2one('res.bank', 'Bank'),
        'acc_number': fields.char('Account Number', size=64),
        'pos': fields.char('Point of Sale', size=64),
        'key': fields.char('Key', size=64),
        'is_registered': fields.function(_is_registered, fnct_inv=_set_registered, string='Is registered to CNPS', type='boolean', store=True),
        #'has_contract': fields.function(_has_contract, fnct_inv=_set_contract, string='Has contract', type='boolean', store=True),
        'has_contract': fields.boolean(string='Has contract'),
        'attachment_ids': fields.many2many("ir.attachment", "hr_employee_attachment_rel",
                                           "attachment_id", "contract_id", "Attachments"),

    }

    _defaults = {
        'has_contract': False,
        'country_id': lambda self, cr, uid, context: self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'cm')[1],
    }

    def create(self, cr, uid, values, context=None):
        #Create partner
        val = {
            'name': values['name'],
            'street': 'street' in values and values['street'] or False,
            'street2': 'street2' in values and values['street2'] or False,
            'zip': 'zip' in values and values['zip'] or False,
            'city': 'city' in values and values['city'] or False,
            'state_id': 'state_id' in values and values['state_id'] or False,
            'country_id': 'country_id' in values and values['country_id'] or False,
            'customer': False,
        }
        # get default account
        account_ids = self.pool.get('account.account').search(cr, uid, [('code', '=', '422000')], context=context)
        val['property_account_payable'] = account_ids and account_ids[0] or False
        val['property_account_receivable'] = account_ids and account_ids[0] or False
        partner_id = self.pool.get('res.partner').create(cr, uid, val, context=context)
        values['address_home_id'] = partner_id
        #Create bank account
        if 'acc_number' in values and values['acc_number']:
            vals = {
                'acc_number': values['acc_number'] if 'acc_number' in values else False,
                'pos': values['pos'] if 'pos' in values else False,
                'key': values['key'] if 'key' in values else False,
                'partner_id': partner_id,
                'bank': 'bank' in values and values['bank'] or False,
                'state': self.pool.get('res.partner.bank')._bank_type_get(cr, uid, context=context)[0][0]
            }
            #if(vals['bank'] and not vals['acc_number'] or not vals['pos'] or not vals['key']) or (not vals['bank'] and vals['acc_number'] or not vals['pos'] or not vals['key']) or (not vals['bank'] or not vals['acc_number'] and vals['pos'] or not vals['key']) or (vals['bank'] and not vals['acc_number'] or not vals['pos'] and vals['key']):
            #        raise osv.except_osv(_('Error'), _('Information about bank account are missing'))

            bank_account_id = self.pool.get('res.partner.bank').create(cr, uid, vals, context=context)
            values['bank_account_id'] = bank_account_id
        return super(hr_employee, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        partner_id = None
        for record in self.browse(cr, uid, ids, context=context):
            val = {
                'name': 'name' in values and values['name'] or record.name,
                'street': 'street' in values and values['street'] or record.street,
                'street2': 'street2' in values and values['street2'] or record.street2,
                'zip': 'zip' in values and values['zip'] or record.zip,
                'city': 'city' in values and values['city'] or record.city,
                'state_id': 'state_id' in values and values['state_id'] or record.state_id and record.state_id.id,
                'country_id': 'country_id' in values and values['country_id'] or record.country_id and record.country_id.id,
            }
            if not record.address_home_id:
                partner_id = self.pool.get('res.partner').create(cr, uid, val, context=context)
                values['address_home_id'] = partner_id
            else:
                self.pool.get('res.partner').write(cr, uid, record.address_home_id.id, val, context=context)
            #Create bank account
            vals = {
                'acc_number': 'acc_number' in values and values['acc_number'] or record.acc_number,
                'pos': 'pos' in values and values['pos'] or record.pos,
                'key': 'key' in values and values['key'] or record.key,
                'partner_id': partner_id or record.address_home_id and record.address_home_id.id,
                'bank': 'bank' in values and values['bank'] or record.bank.id,
                'state': self.pool.get('res.partner.bank')._bank_type_get(cr, uid, context=context)[0][0]
            }
            #if(vals['bank'] and not vals['acc_number'] or not vals['pos'] or not vals['key']) or (not vals['bank'] and vals['acc_number'] or not vals['pos'] or not vals['key']) or (not vals['bank'] or not vals['acc_number'] and vals['pos'] or not vals['key']) or (vals['bank'] and not vals['acc_number'] or not vals['pos'] and vals['key']):
            #    raise osv.except_osv(_('Error'), _('Information about bank account are missing'))
            if not record.bank_account_id and vals['acc_number']:
                bank_account_id = self.pool.get('res.partner.bank').create(cr, uid, vals, context=context)
                values['bank_account_id'] = bank_account_id
            elif record.bank_account_id:
                #bank_account_id = record.bank_account_id.id
                self.pool.get('res.partner.bank').write(cr, uid, record.bank_account_id.id, vals, context=context)

            return super(hr_employee, self).write(cr, uid, ids, values, context=context)

hr_employee()


class integc_hr_registration_request(osv.osv):
    """
    Registration request to social security
    """
    _name = 'integc.hr.registration.request'
    _description = 'Social security registration request'

    def _get_employee_count(self, cr, uid, ids, name, value, args=None, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = len(record.request_line_ids)
        return res

    def _set_employee_count(self, cr, uid, ids, name, value, args=None, context=None):
        if value:
            this = self.browse(cr, uid, ids, context=context)
            self.write(cr, uid, ids, {'employee_count': len(this.request_line_ids)})
            return len(this.request_line_ids)

    def _get_date_from(self, cr, uid, ids, name, value, args=None, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=None):
            res[record.id] = subtract_month(datetime.now(), 4)
        return res

    def _set_date_from(self, cr, uid, ids, name, value, args=None, context=None):
        res = subtract_month(datetime.now(), 4)
        self.write(cr, uid, ids, {'date_form': res}, context=context)
        return res

    def _get_date_to(self, cr, uid, ids, name, value, args=None, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=None):
            res[record.id] = str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]
        return res

    def _set_date_to(self, cr, uid, ids, name, value, args=None, context=None):
        res = str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]
        self.write(cr, uid, ids, {'date_to': res}, context=context)
        return res

    #def _registration_search(self, cursor, user, obj, name, args, context=None):
    #    ids = set()
    #    for cond in args:
    #        amount = cond[2]
    #        if isinstance(cond[2],(list,tuple)):
    #            if cond[1] in ['in','not in']:
    #                amount = tuple(cond[2])
    #            else:
    #                continue
    #        else:
    #            if cond[1] in ['=like', 'like', 'not like', 'ilike', 'not ilike', 'in', 'not in', 'child_of']:
    #                continue
    #        date_from = subtract_month(datetime.now(), 4)
    #        date_to = str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]
    #        logging.warning('Date from : %s - Date To : %s' % (date_from, date_to))
    #        cursor.execute("select id from integc_hr_registration_request group by id where date <= %s  and date >= %s" % (date_to,date_from))
    #        res_ids = set(id[0] for id in cursor.fetchall())
    #        ids = ids and (ids & res_ids) or res_ids
    #    if ids:
    #        return [('id', 'in', tuple(ids))]
    #    return [('id', '=', '0')]


    _columns = {
        'date': fields.datetime('Date Request'),
        'date_validation': fields.date('Date Validation'),
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'request_line_ids': fields.one2many('integc.hr.registration.request.line', 'registration_id', 'Request Line', required=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('waiting', 'Waiting'),
            ('validate', 'Validated'),
            ('cancel', 'Canceled')
        ], string='State'),
        'employee_count': fields.function(_get_employee_count, fnct_inv=_set_employee_count, string='Employee Count', type='integer', store=True),
        'external_reference': fields.char('External Reference', size=64),
        #'date_from': fields.function(_get_date_from, type='date', string='Date From', method=True, fnct_search=_registration_search),
        #'date_to': fields.function(_get_date_to, type='date', string='Date To', method=True, fnct_search=_registration_search),
    }

    _order = 'date desc, id'
    _defaults = {
        'state': 'draft',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def create(self, cr, uid, values, context=None):
        if 'request_line_ids' not in values or not values['request_line_ids']:
            raise osv.except_osv(_('Operation not allowed!'), _('No employee registered. You must write at least one employee'))
        return super(integc_hr_registration_request, self).create(cr, uid, values, context=context)

    def validate_registration(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            for line in record.request_line_ids:
                if not line.ssnid or not line.date_registration:
                    raise osv.except_osv(_('Operation not allowed'), _('Neither social security number or date registration is not defined for %s' % line.employee_id.name))
                self.pool.get('hr.employee').write(cr, uid, [line.employee_id.id], {'ssnid': line.ssnid}, context=context)
                #self.pool.get('integc.hr.registration.request.line').write(cr, uid, line.id, {'state': 'validate', 'date_registration': record.date_registration})
        return self.write(cr, uid, ids, {'state': 'validate', 'date_validation': time.strftime('%Y-%m-%d')}, context=context)

    def cancel_registration(self, cr, uid, ids, context=None):
        #for record in self.browse(cr, uid, ids, context=context):
        #    for line in record.request_line_ids:
        #        self.pool.get('integc.hr.registration.request.line').write(cr, uid, line.id, {'state': 'cancel'})
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def action_waiting(self, cr, uid, ids, context=None):
        #for record in self.browse(cr, uid, ids, context=context):
        #    for line in record.request_line_ids:
        #        self.pool.get('integc.hr.registration.request.line').write(cr, uid, line.id, {'state': 'waiting'})
        self.write(cr, uid, ids, {'state': 'waiting'}, context=context)
        return True

    #def _check_employee(self, cr, uid, employee_id, context=None):
    #

integc_hr_registration_request()


class integc_hr_registration_request_line(osv.osv):
    """
    Registration request line
    """
    _name = 'integc.hr.registration.request.line'
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', domain="[('ssnid', '=', None)]"),
        'date': fields.related('registration_id', 'date', type='datetime', string='Date request'),
        'ssnid': fields.char('Social Security Number', size=64),
        'date_registration': fields.date('Date registration'),
        'registration_id': fields.many2one('integc.hr.registration.request', 'Registration Request'),
        'state': fields.related('registration_id', 'state', type='selection', string='State', selection=[
            ('draft', 'Draft'),
            ('waiting', 'Waiting'),
            ('validate', 'Validated'),
            ('cancel', 'Canceled')
        ], readonly=True, store=True),
    }
integc_hr_registration_request_line()


class hr_department(osv.osv):
    """
    Department
    """
    _name = 'hr.department'
    _inherit = 'hr.department'
    _columns = {
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', ondelete="cascade", required=False),
		'label' : fields.char('Libelle',size=255)
    }
	
    def create(self, cr, uid, values, context=None):
        parent_id = False
        if 'parent_id' in values and values['parent_id']:
            parent = self.browse(cr, uid, values['parent_id'], context=context)
            parent_id = parent and parent.analytic_account_id and parent.analytic_account_id.id or False
        values['analytic_account_id'] = self.pool.get('account.analytic.account').create(cr, uid, {
            'name': values['name'],
            'parent_id': parent_id
        }, context=context)
        return super(hr_department, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        parent_id = False
        if 'parent_id' in values and values['parent_id']:
            parent = self.browse(cr, uid, values['parent_id'], context=context)
            parent_id = parent.analytic_account_id.id
        name = 'name' in values and values['name'] or False
        for record in self.browse(cr, uid, ids, context=context):
            vals = {
                'name': name or record.name,
                'parent_id': parent_id
            }
            if record.analytic_account_id:
                self.pool.get('account.analytic.account').write(cr, uid, record.analytic_account_id.id, vals, context=context)
            else:
                values['analytic_account_id'] = self.pool.get('account.analytic.account').create(cr, uid, vals, context=context)
        return super(hr_department, self).write(cr, uid, ids, values, context=context)
	
hr_department()

class integc_hr_category(osv.osv):
    """
    Salary Category
    """
    _name = "integc.hr.category"
    _description = "Salary Category"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'note': fields.text('Note'),
        'structure_id': fields.many2one('hr.payroll.structure', 'Salary Structure', required=True),
        'transport_allowance': fields.float('Transport Allowance', digits=(16,2)),
        'housing_allowance': fields.float('housing Allowance', digits=(16,2)),
        'representation_fees': fields.float('Representation Fees', digits=(16,2)),
        'risk_prime': fields.float('Risk Prime', digits=(16,2)),
        'responsibility_prime': fields.float('Responsibility Prime', digits=(16,2)),
    }
    _sql_constraints = [('integc_category_name_unique','unique(name)', _('Category name already exists'))]
    _defaults = {
        'transport_allowance': 0.0,
        'housing_allowance': 0.0,
        'representation_fees': 0.0,
        'risk_prime': 0.0,
        'responsibility_prime': 0.0,
    }
integc_hr_category()


class integc_hr_grade(osv.osv):
    """
    Salary grade
    """
    _name = 'integc.hr.grade'
    _description = 'Salary Grade'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'note': fields.text('Note'),
    }
    _sql_constraints = [('integc_grade_name_unique','unique(name)', _('Grade name already exists'))]
integc_hr_grade()


class integc_hr_salary_grid(osv.osv):
    """
    Salary grid
        - Category
        - Grade
        - wage salary interval
    """
    _name = 'integc.hr.salary.grid'
    _description = "Salary Grid"
    _columns = {
        'name':  fields.char('Name', size=128, readonly=True),
        'category_id': fields.many2one('integc.hr.category', 'Category', required=True),
        'grade_id': fields.many2one('integc.hr.grade', 'Grade', required=True),
        'wage_min': fields.float('Wage Minimal', digits=(16,2), required=True, help="Basic Minimal Salary for this grid"),
        'wage_max': fields.float('Wage Maximal', digits=(16,2), required=True, help="Basic Maximal Salary for this grid"),
        'structure_id': fields.related('category_id', 'structure_id', relation='hr.payroll.structure', type='many2one', store=False, readonly=True, string="Salary Structure"),
    }

    def _check_wage(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.wage_min > record.wage_max:
                return False
        return True

    _constraints = [(_check_wage,_("'Wage Minimal' must be lower than 'Wage Maximal'."), ['wage_min', 'wage_max'])]
    _sql_constraints = [('integc_salary_grid_name_unique','unique(name)', _('Salary grid name already exists'))]

    def create(self, cr, uid, values, context=None):
        category = self.pool.get('integc.hr.category').browse(cr, uid, values['category_id'], context=context)
        grade = self.pool.get('integc.hr.grade').browse(cr, uid, values['grade_id'], context=context)
        if category and grade:
            values['name'] = category.name + " - " + grade.name
        return super(integc_hr_salary_grid, self).create(cr, uid, values, context=context)

    #def write(self, cr, uid, ids, values, context=None):
    #    for record in self.browse(cr, uid, ids, context=context):
    #        if 'category_id' not in values:
    #            category = record.category_id
    #        else:
    #            category = self.pool.get('integc.hr.category').browse(cr, uid, [values['category_id']], context=context)[0]
    #        if 'grade_id' not in values:
    #            grade = record.grade_id
    #        else:
    #            grade = self.pool.get('integc.hr.grade').browse(cr, uid, [values['grade_id']], context=context)[0]
    #        if category and grade:
    #            values['name'] = category.name + " - " + grade.name
    #        return super(integc_hr_salary_grid, self).write(cr, uid, ids, values, context=context)

    #def onchange_category(self, cr, uid, ids, cat, context=None):
    #    if cat:
    #        cat = self.pool.get('integc.hr.category').browse(cr, uid, cat, context=context)
    #    return {
    #        'value': {
    #            ''
    #        }
    #    }

integc_hr_salary_grid()


class hr_contract(osv.osv):
    """
    Hr contract
    """
    _inherit = 'hr.contract'
    _name = "hr.contract"
    _description = 'Employee Contract'

    def _get_seniority(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = ((datetime.strptime(time.strftime('%Y-%m-%d'),'%Y-%m-%d') - datetime.strptime(record.date_start, '%Y-%m-%d')).days)/365
        return res

    def _set_seniority(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            this = self.browse(cr, uid, id, context=context)
            seniority = ((datetime.strptime(time.strftime('%Y-%m-%d'),'%Y-%m-%d') - datetime.strptime(this.date_start, '%Y-%m-%d')).days)/365
            self.write(cr, uid, id, {'seniority': seniority})
            return seniority

    def _get_first_date(self, cr, uid, id, name, value, args=None, context=None):
        return time.strftime('%Y-%m-01')

    def _get_last_date(self, cr, uid, id, name, value, args=None, context=None):
        return str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]

    def _get_type(self, cr, uid, context=None):
        #type_ids = self.pool.get('hr.contract.type').search(cr, uid, [('name', '=', 'CDD')])
        #return type_ids and type_ids[0] or False
        return False


    _columns = {
        'name': fields.char('Contract Reference', size=64, required=False),
        'salary_grid_id': fields.many2one('integc.hr.salary.grid', 'Salary Grid'),
        #'category_id': fields.related('salary_grid_id', 'category_id', relation='integc.hr.category',type='many2one', string='Category', readonly=True, store=True),
        #'grade_id': fields.related('salary_grid_id', 'category_id', relation='integc.hr.category',type='many2one', string='Category', readonly=True, store=True),
        'category_id': fields.many2one('integc.hr.category', 'Category'),
        'grade_id': fields.many2one('integc.hr.grade', 'Grade'),
        'wage_min': fields.related('salary_grid_id', 'wage_min', type='float', string='Wage Minimal', readonly=True),
        'wage_max': fields.related('salary_grid_id', 'wage_max', type='float', string='Wage Maximal', readonly=True),
        'seniority': fields.function(_get_seniority, fnct_inv=_set_seniority, string='Seniority', type='integer'),
        'job_id': fields.related('employee_id','job_id', type='many2one', relation='hr.job', string="Job Title", readonly=True),
        'project_id': fields.many2one('project.project', 'Project'),
        #'analytic_account_id': fields.related('project_id', 'analytic_account_id', type='many2one', relation='account.analytic.account', string="Analytic Account", readonly=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('signature_director', 'Waiting for signature of director'),
            ('signature_employee', 'Waiting for signature of employee'),
            ('progress', 'Progress'),
            ('done', 'Completed'),
            ('cancel', 'Cancel')
        ], string='State'),
        'date_cancel': fields.datetime('Date Cancel'),
        'date_signature_director': fields.datetime('Date Signature Director'),
        'date_signature_employee': fields.datetime('Date Signature Employee'),
        'date_from': fields.function(lambda *a,**k:{}, method=True, type='date',string="Date from"),
        'date_to': fields.function(lambda *a,**k:{}, method=True, type='date',string="Date to"),
        'attachment_ids': fields.many2many("ir.attachment", "hr_partner_contract_attachment_rel",
                                           "attachment_id", "contract_id", "Attachments"),
    }

    _defaults = {
        'state': 'draft',
        'journal_id': lambda self, cr, uid, context: self.pool.get('ir.model.data').get_object_reference(cr, uid, 'integc', 'account_journal_payroll')[1]
    }

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel', 'date_cancel': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
        employee_obj = self.pool.get('hr.employee')
        for record in self.browse(cr, uid, ids, context):
            employee_obj.write(cr, uid, [record.employee_id.id], {'has_contract': False}, context=context)
        return True

    def action_progress(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'progress', 'date_signature_employee': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
        employee_obj = self.pool.get('hr.employee')
        for record in self.browse(cr, uid, ids, context):
            employee_obj.write(cr, uid, [record.employee_id.id], {'has_contract': True}, context=context)
        return True

    def action_signature_director(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'signature_director'}, context=context)
        return True

    def action_signature_employee(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'signature_employee', 'date_signature_employee': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        employee_obj = self.pool.get('hr.employee')
        for record in self.browse(cr, uid, ids, context):
            employee_obj.write(cr, uid, [record.employee_id.id], {'has_contract': True}, context=context)
        return True

    def check_done(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.date_end and record.date_end < time.strftime('%Y-%m-%d'):
                return True
        return False

    def create(self, cr, uid, values, context=None):
        self._check_salary_grid(cr, uid, values, context=context)
        if 'name' not in values:
            values['name'] = self.pool.get('ir.sequence').get(cr, uid, 'hr.contract')
        employee = self.pool.get('hr.employee').browse(cr, uid, values['employee_id'], context=context)
        values['analytic_account_id'] = employee and employee.department_id and employee.department_id.analytic_account_id.id
        #logging.warning("values['analytic_account_id'] = %s" % values['analytic_account_id'])
        if 'project_id' in values and values['project_id']:
            project = self.pool.get('project.project').browse(cr, uid, values['project_id'], context=context)
            values['analytic_account_id'] = project and project.analytic_account_id.id or False
        #logging.warning("values['analytic_account_id'] = %s" % values['analytic_account_id'])
        return super(hr_contract, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if 'project_id' in values and values['project_id']:
            project = self.pool.get('project.project').browse(cr, uid, values['project_id'], context=context)
            values['analytic_account_id'] = project and project.analytic_account_id.id or False
        else:
            for record in self.browse(cr, uid, ids, context=context):
                if 'category_id' in values or 'grade_id' in values:
                    if not 'category_id' in values:
                        values['category_id'] = record.category_id.id
                    if not 'grade_id' in values:
                        values['grade_id'] = record.grade_id.id
                    self._check_salary_grid(cr, uid, values, context=context)
                values['analytic_account_id'] = record.employee_id.department_id.analytic_account_id.id if record.employee_id and record.employee_id.department_id and record.employee_id.department_id.analytic_account_id else False
        #logging.warning(values)
        return super(hr_contract, self).write(cr, uid, ids, values, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'hr.contract'),
            'state': 'draft'
        })
        return super(hr_contract, self).copy(cr, uid, id, default, context)

    def _check_wage(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.salary_grid_id and (record.wage < record.salary_grid_id.wage_min or record.wage > record.salary_grid_id.wage_max):
                return False
        return True

    #_constraints = [(_check_wage, _("Wage must be range in salary grid wage min and salary grid wage max."), ['wage'])]

    def onchange_category_grade(self, cr, uid, ids, category, grade, context=None):
        salary_grid = None
        #logging.warning('Cat %s - Grad %s' % (category, grade))
        if category:
            category = self.pool.get('integc.hr.category').browse(cr, uid, category, context=context)
            if grade:
                grade = self.pool.get('integc.hr.grade').browse(cr, uid, grade, context=context)
                salary_grid_id = self.pool.get('integc.hr.salary.grid').search(cr, uid, [('category_id', '=', category.id), ('grade_id', '=', grade.id)])
                salary_grid = self.pool.get('integc.hr.salary.grid').browse(cr, uid, salary_grid_id, context=context)
                salary_grid = salary_grid and salary_grid[0]
        return {
            'value': {
                'category_id': category and category.id or False,
                'struct_id': category and category.structure_id.id or False,
                'salary_grid_id': salary_grid and salary_grid.id or False,
                'wage_min': salary_grid and salary_grid.wage_min or 0.0,
                'wage_max': salary_grid and salary_grid.wage_max or 0.0,
            }
        }

    def onchange_salary_grid(self, cr, uid, ids, salary_grid, context=None):
        if salary_grid:
            salary_grid = self.pool.get('integc.hr.salary.grid').browse(cr, uid, salary_grid, context=context)
        structure = salary_grid and salary_grid.category_id and salary_grid.category_id.structure_id and salary_grid.category_id.structure_id.id or False
        wage_min = salary_grid and salary_grid.wage_min or 0.0
        wage_max = salary_grid and salary_grid.wage_max or 0.0
        return {
            'value': {
                'struct_id': structure,
                'wage_min': wage_min,
                'wage_max': wage_max,
            }
        }

    def _check_salary_grid(self, cr, uid, values, context=None):
        if not 'salary_grid_id' in values:
            category = values['category_id']
            grade = values['grade_id']
            salary_grid_ids = self.pool.get('integc.hr.salary.grid').search(cr, uid, [('category_id', '=', category), ('grade_id', '=', grade)], context=context)
            #logging.warning(salary_grid_ids)
            salary_grid = self.pool.get('integc.hr.salary.grid').browse(cr, uid, salary_grid_ids, context=context)
            #logging.warning(salary_grid)
            if not salary_grid:
                raise osv.except_osv(_('Operation not allowed'), _('There is not salary grid defined for this category and grade'))
            salary_grid = salary_grid and salary_grid[0]
            values['salary_grid_id'] = salary_grid and salary_grid.id or None
            values['struct_id'] = salary_grid and salary_grid.structure_id.id or None
        return True

    def scheduler_close_contract(self, cr, uid, context=None):
        cr.execute("select c.id from hr_contract c where c.date_end is not null and c.state = 'progress' and c.date_end < '%s'" % time.strftime('%Y-%m-%d'))
        ids = [x[0] for x in cr.fetchall()]
        if ids:
            self.write(cr, uid, ids, {'state', '=', 'done'})
        return True

    def run_scheduler(self, cr, uid, context=None):
        self.scheduler_close_contract(cr, uid, context=context)
        return True

hr_contract()


class hr_payslip_run(osv.osv):
    _name = 'hr.payslip.run'
    _inherit = 'hr.payslip.run'

    def _get_irpp(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'IRPP')
        return res

    def _set_irpp(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'IRPP')
                self.write(cr, uid, id, {'irpp': res})
                return res

    def _get_cac(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'CAC')
        return res

    def _set_cac(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'CAC')
                self.write(cr, uid, id, {'cac': res})
                return res

    def _get_cfc_patronal(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'CFC_PATRONAL')
        return res

    def _set_cfc_patronal(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'CFC_PATRONAL')
                self.write(cr, uid, id, {'cfc_patronal': res})
                return res

    def _get_cfc_salarial(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'CFC')
        return res

    def _set_cfc_salarial(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'CFC')
                self.write(cr, uid, id, {'cfc_salarial': res})
                return res

    def _get_fne(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'FNE')
        return res

    def _set_fne(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'FNE')
                self.write(cr, uid, id, {'fne': res})
                return res

    def _get_tdl(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'TDL')
        return res

    def _set_tdl(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'TDL')
                self.write(cr, uid, id, {'tdl': res})
                return res

    def _get_rav(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'RAV')
        return res

    def _set_rav(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'RAV')
                self.write(cr, uid, id, {'rav': res})
                return res

    def _get_prest_fam(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'PREST_FAM')
        return res

    def _set_prest_fam(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'PREST_FAM')
                self.write(cr, uid, id, {'prest_fam': res})
                return res

    def _get_pens_viel(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'TOTAL_PENSION')
        return res

    def _set_pens_viel(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'TOTAL_PENSION')
                self.write(cr, uid, id, {'pens_viel': res})
                return res

    def _get_acc_trav(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'ACC_TRAV')
        return res

    def _set_acc_trav(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'ACC_TRAV')
                self.write(cr, uid, id, {'acc_trav': res})
                return res

    def _get_charge_patronale(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'TOTAL_IMPOT')
            #res[record.id] = record.irpp + record.cac + record.fne + record.tdl + record.rav + record.cfc_salarial + record.cfc_patronal
        return res

    def _set_charge_patronale(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_payslip_amount_by_rule_code(cr, uid, record.slip_ids, 'TOTAL_IMPOT')
                #res = record.irpp + record.cac + record.fne + record.tdl + record.rav + record.cfc_salarial + record.cfc_patronal
                self.write(cr, uid, id, {'total_charge_patronale': res})
                return res

    def _get_charge_sociale(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.get_total_amount_by_category(cr, uid, record.slip_ids, 'TOTAL_CHARGE')
        return res

    def _set_charge_sociale(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            for record in self.browse(cr, uid, id, context=context):
                res = self.get_total_amount_by_category(cr, uid, record.slip_ids, 'TOTAL_CHARGE')
                self.write(cr, uid, id, {'total_charge_sociale': res})
                return res

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'irpp': fields.function(_get_irpp, fnct_inv=_set_irpp, string='IRPP', type='float', digits=(32,0)),
        'cac': fields.function(_get_cac, fnct_inv=_set_cac, string='CAC', type='float', digits=(32,0)),
        'cfc_patronal': fields.function(_get_cfc_patronal, fnct_inv=_set_cfc_patronal, string='CFC Patronal', type='float', digits=(32,0)),
        'cfc_salarial': fields.function(_get_cfc_salarial, fnct_inv=_set_cfc_salarial, string='CFC Salarial', type='float', digits=(32,0)),
        'fne': fields.function(_get_fne, fnct_inv=_set_fne, string='FNE', type='float', digits=(32,0)),
        'tdl': fields.function(_get_tdl, fnct_inv=_set_tdl, string='TDL', type='float', digits=(32,0)),
        'rav': fields.function(_get_rav, fnct_inv=_set_rav, string='RAV', type='float', digits=(32,0)),
        'prest_fam': fields.function(_get_prest_fam, fnct_inv=_set_prest_fam, string='Prestations Familiales', type='float', digits=(32,0)),
        'pens_viel': fields.function(_get_pens_viel, fnct_inv=_set_pens_viel, string='Pension Vieillesse', type='float', digits=(32,0)),
        'acc_trav': fields.function(_get_acc_trav, fnct_inv=_set_acc_trav, string='Accident de travail', type='float', digits=(32,0)),
        'total_charge_patronale': fields.function(_get_charge_patronale, fnct_inv=_set_charge_patronale, string='Total Charges', type='float', digits=(32,0)),
        'total_charge_sociale': fields.function(_get_charge_sociale, fnct_inv=_set_charge_sociale, string='Total Prestations Sociales', type='float', digits=(32,0)),
    }

    _defaults = {
        'company_id': _default_company,
        'state': 'draft',
        'journal_id': lambda self, cr, uid, context: self.pool.get('ir.model.data').get_object_reference(cr, uid, 'integc', 'account_journal_payroll')[1]
    }

    def get_payslip_amount_by_rule_code(self, cr, uid, obj, code):
        res = 0
        #logging.warning('%s - %s' % (obj, code))
        payslip_line = self.pool.get('hr.payslip.line')
        line_ids = payslip_line.search(cr, uid, [('slip_id', '=', obj.id),('code', '=', code )])
        for line in payslip_line.browse(cr, uid, line_ids):
            #logging.warning(line)
            res += line.total
        return res

    def get_total_payslip_amount_by_rule_code(self, cr, uid, objects, code):
        res = 0
        for obj in objects:
            res += self.get_payslip_amount_by_rule_code(cr, uid, obj, code)
        #logging.warning('%s - %s' % (code, res))
        return round(res)

    def get_total_by_rule_category(self, cr, uid, obj, code):
        payslip_line = self.pool.get('hr.payslip.line')
        rule_cate_obj = self.pool.get('hr.salary.rule.category')

        cate_ids = rule_cate_obj.search(cr, uid, [('code', '=', code)])

        category_total = 0
        #logging.warning(code)
        if cate_ids:
            line_ids = payslip_line.search(cr, uid, [('slip_id', '=', obj.id),('category_id.id', '=', cate_ids[0] )])
            for line in payslip_line.browse(cr, uid, line_ids):
                #logging.warning('%s - %s' % (code, line.total))
                category_total += line.total

        return round(category_total)

    def get_total_amount_by_category(self, cr, uid, objects, code):
        res = 0
        for obj in objects:
            res += self.get_total_by_rule_category(cr, uid, obj, code)
        return round(res)

    def print_payslip(self, cr, uid, ids, context=None):
        #assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        payslip = self.pool.get('hr.payslip')
        payslip_ids = []
        for record in self.browse(cr, uid, ids, context=context):
            for slip in record.slip_ids:
                payslip_ids.append(slip.id)
        if not payslip_ids:
            raise osv.except_osv(_('Operation not allowed!'), _('There is no payslip to print'))
        datas = {
            'ids': payslip_ids,
            'model': 'hr.payslip',
            'form': payslip.read(cr, uid, payslip_ids, context=context)
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'integc.payslip',
            'datas': datas,
            'nodestroy': True
        }

    def print_journal(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        datas = {
            'ids': ids,
            'model': 'hr.payslip.run',
            'form': self.read(cr, uid, ids, context=context)
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'payslip.run',
            'datas': datas,
            'nodestroy': True
        }


hr_payslip_run()


class hr_payslip(osv.osv):
    """
    Payslip
    """
    _name = 'hr.payslip'
    _inherit = 'hr.payslip'
    _columns = {
        'input_line_ids': fields.one2many('hr.payslip.input', 'payslip_id', 'Payslip Inputs', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'is_paid': fields.boolean('Paid', help='determines if the payslip is paid'),
        'date_payment': fields.datetime('Date Payment'),
    }

    _defaults = {
        'is_paid': False,
    }

    def action_paid(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'is_paid': True, 'date_payment': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
        return True

    def print_payslip(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        datas = {
            'ids': ids,
            'model': 'hr.payslip',
            'form': self.read(cr, uid, ids[0], context=context)
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'integc.payslip',
            'datas': datas,
            'nodestroy': True
        }

    def process_sheet(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Payroll')
        timenow = time.strftime('%Y-%m-%d')

        for slip in self.browse(cr, uid, ids, context=context):
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            if not slip.period_id:
                ctx = dict(context or {}, account_period_prefer_normal=True)
                search_periods = period_pool.find(cr, uid, slip.date_to, context=ctx)
                period_id = search_periods[0]
            else:
                period_id = slip.period_id.id

            default_partner_id = slip.employee_id.address_home_id.id
            name = _('Payslip of %s') % (slip.employee_id.name)
            move = {
                'narration': name,
                'date': timenow,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'period_id': period_id,
            }
            for line in slip.details_by_salary_rule_category:
                amt = slip.credit_note and -line.total or line.total
                partner_id = line.salary_rule_id.register_id.partner_id and line.salary_rule_id.register_id.partner_id.id or default_partner_id
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id

                if debit_account_id:

                    debit_line = (0, 0, {
                    'name': line.name,
                    'date': timenow,
                    'partner_id': (line.salary_rule_id.register_id.partner_id or line.salary_rule_id.account_debit.user_type.code in ('receivable', 'payable', 'dettes')) and partner_id or False,
                    'account_id': debit_account_id,
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                    'debit': amt > 0.0 and amt or 0.0,
                    'credit': amt < 0.0 and -amt or 0.0,
                    'analytic_account_id': line.salary_rule_id.analytic_account_id and line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id and slip.contract_id.analytic_account_id.id or False,
                    'tax_code_id': line.salary_rule_id.account_tax_id and line.salary_rule_id.account_tax_id.id or False,
                    'tax_amount': line.salary_rule_id.account_tax_id and amt or 0.0,
                })
                    line_ids.append(debit_line)
                    debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if credit_account_id:

                    credit_line = (0, 0, {
                    'name': line.name,
                    'date': timenow,
                    'partner_id': (line.salary_rule_id.register_id.partner_id or line.salary_rule_id.account_credit.user_type.code in ('receivable', 'payable', 'dettes')) and partner_id or False,
                    'account_id': credit_account_id,
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                    'debit': amt < 0.0 and -amt or 0.0,
                    'credit': amt > 0.0 and amt or 0.0,
                    'analytic_account_id': line.salary_rule_id.analytic_account_id and line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id and slip.contract_id.analytic_account_id.id or False,
                    'tax_code_id': line.salary_rule_id.account_tax_id and line.salary_rule_id.account_tax_id.id or False,
                    'tax_amount': line.salary_rule_id.account_tax_id and amt or 0.0,
                })
                    line_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_id = slip.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise osv.except_osv(_('Configuration Error!'),_('The Expense Journal "%s" has not properly configured the Credit Account!')%(slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'date': timenow,
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_id = slip.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise osv.except_osv(_('Configuration Error!'),_('The Expense Journal "%s" has not properly configured the Debit Account!')%(slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'date': timenow,
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'period_id': period_id,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
            self.write(cr, uid, [slip.id], {'move_id': move_id, 'period_id' : period_id}, context=context)
            if slip.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context=context)
        return True
        #return super(hr_payslip, self).process_sheet(cr, uid, [slip.id], context=context)

        #TODO move this function into hr_contract module, on hr.employee object
    def get_contract(self, cr, uid, employee, date_from, date_to, context=None):
        """
        @param employee: browse record of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        contract_obj = self.pool.get('hr.contract')
        clause = []
        #a contract is valid if it ends between the given dates
        clause_1 = ['&',('date_end', '<=', date_to),('date_end','>=', date_from)]
        #OR if it starts between the given dates
        clause_2 = ['&',('date_start', '<=', date_to),('date_start','>=', date_from)]
        #OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = [('date_start','<=', date_from),'|',('date_end', '=', False),('date_end','>=', date_to)]
        clause_final =  [('employee_id', '=', employee.id), ('state', '=', 'progress'),'|','|'] + clause_1 + clause_2 + clause_3
        contract_ids = contract_obj.search(cr, uid, clause_final, context=context)
        return contract_ids

hr_payslip()


class hr_payslip_input(osv.osv):
    _name = 'hr.payslip.input'
    _inherit = 'hr.payslip.input'
    _columns = {
        'code': fields.selection([
            ('AVANSAL', 'Avance sur Salaire'),
            ('PRIMREND', 'Prime Rendement'),
            ('PRIMPROJ', 'Prime Projet'),
            ('REMBC', 'Remboursement Crédit'),
            ('CONGE', 'Congé'),
        ], 'Code', required=True),
    }
hr_payslip_input()

