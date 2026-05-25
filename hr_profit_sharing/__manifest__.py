{
    'name': 'HR Profit Sharing',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Employee Profit Sharing Management',
    'depends': [
        'hr',
        'hr_payroll',
        'mail',
    ],

    'data': [
        'security/ir.model.access.csv',

        # Views
        'views/profit_sharing_views.xml',
        'views/hr_employee_views.xml',
    ],

    'installable': True,
    'application': False,
}