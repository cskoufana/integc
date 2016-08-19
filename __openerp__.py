# -*- coding: utf-8 -*-
#__author__ = 'yenke'

{
    'name' : 'INTEGC',
    'version' : '0.1.1',
    'author' : 'Appacheur',
    'sequence': 20,
    'category': '',
    'summary' : 'Human resources, Project, Accounting, Sale Order',
    'description' : """
""",
    'depends' : [
        'base',
        'hr',
        'hr_contract',
        'hr_payroll_account',
    ],
    'data' : [
        'security/integc_security.xml',
        'security/ir.model.access.csv',
        'hr/hr_data.xml',
        'hr/hr_view.xml',
        'hr/report/hr_report_view.xml',
        'hr/wizard/hr_payroll_journal_report_view.xml',
        'res/res_partner_view.xml'
    ],

    'demo': [],

    'installable' : True,
    'application' : True,
}
