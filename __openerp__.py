# -*- coding: utf-8 -*-
#__author__ = 'yenke'

{
    'name' : 'INTEGC',
    'version' : '0.1.5',
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
        'project',
        'product',
        'budget'
    ],
    'data' : [
        'security/integc_security.xml',
        'security/ir.model.access.csv',
        'hr/hr_data.xml',
        'hr/hr_sequence.xml',
        'hr/wizard/hr_wizard.xml',
        'hr/hr_view.xml',
        'hr/hr_workflow.xml',
        'hr/report/hr_report_view.xml',
        'hr/wizard/hr_payroll_journal_report_view.xml',
        'hr/partner_contract_workflow.xml',
        'hr/partner_contract_view.xml',
        'hr/board_hr_view.xml',
        'budget/budget_view.xml',
        'res/res_partner_view.xml',
        'res/res_bank_view.xml',
        'account/account_invoice_data.xml',
        'account/account_invoice_workflow.xml',
        'account/account_invoice_view.xml',
        'account/report/account_report_view.xml',
        'account/account_voucher_view.xml',
        'market/market_sequence.xml',
        'market/wizard/market_wizard_view.xml',
        'market/market_view.xml',

    ],

    'demo': [],

    'installable' : True,
    'application' : True,
}
