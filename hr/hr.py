# -*- coding: utf-8 -*-
#__author__ = 'yenke'



from openerp.osv import fields, osv
import time
from datetime import datetime
from openerp import tools
from openerp.osv.orm import except_orm
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


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
    }
    _sql_constraints = [('integc_category_name_unique','unique(name)', _('Category name already exists'))]
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


    _columns = {
        'salary_grid_id': fields.many2one('integc.hr.salary.grid', 'Salary Grid'),
        #'category_id': fields.related('salary_grid_id', 'category_id', relation='integc.hr.category',type='many2one', string='Category', readonly=True, store=True),
        #'grade_id': fields.related('salary_grid_id', 'category_id', relation='integc.hr.category',type='many2one', string='Category', readonly=True, store=True),
        'category_id': fields.many2one('integc.hr.category', 'Category'),
        'grade_id': fields.many2one('integc.hr.grade', 'Grade'),
        'wage_min': fields.related('salary_grid_id', 'wage_min', type='float', string='Wage Minimal', readonly=True),
        'wage_max': fields.related('salary_grid_id', 'wage_max', type='float', string='Wage Maximal', readonly=True),
        'seniority': fields.function(_get_seniority, fnct_inv=_set_seniority, string='Seniority', type='integer'),
    }

    def _check_wage(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.salary_grid_id and (record.wage < record.salary_grid_id.wage_min or record.wage > record.salary_grid_id.wage_max):
                return False
        return True

    #_constraints = [(_check_wage, _("Wage must be range in salary grid wage min and salary grid wage max."), ['wage'])]

    def onchange_category_grade(self, cr, uid, ids, category, grade, context=None):
        salary_grid = None
        logging.warning('Cat %s - Grad %s' % (category, grade))
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
            logging.warning(salary_grid_ids)
            salary_grid = self.pool.get('integc.hr.salary.grid').browse(cr, uid, salary_grid_ids, context=context)
            logging.warning(salary_grid)
            if not salary_grid:
                raise osv.except_osv(_('Operation not allowed'), _('There is not salary grid defined for this category and grade'))
            salary_grid = salary_grid and salary_grid[0]
            values['salary_grid_id'] = salary_grid and salary_grid.id or None
            values['struct_id'] = salary_grid and salary_grid.structure_id.id or None
        return True

    def create(self, cr, uid, values, context=None):
        self._check_salary_grid(cr, uid, values, context=context)
        return super(hr_contract, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if 'category_id' in values or 'grade_id' in values:
                if not 'category_id' in values:
                    values['category_id'] = record.category_id.id
                if not 'grade_id' in values:
                    values['grade_id'] = record.grade_id.id
                self._check_salary_grid(cr, uid, values, context=context)
            return super(hr_contract, self).write(cr, uid, ids, values, context=context)

hr_contract()


