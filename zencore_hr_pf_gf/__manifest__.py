{
    'name': 'Zencore Hr PF GF ',
    'version': "19.0.1.0.0",
    'author': "Sohan",
    'depends': ['sale', 'account', 'stock', "hr",
    'hr_payroll',],
    'data': [
        "security/ir.model.access.csv",
        "views/pf_policy_vesting_views.xml",
        "views/pf_policy_views.xml",
        "views/pf_account_views.xml",
        'views/pf_transaction_views.xml',
        'views/pf_interest_rate_views.xml',
        'views/pf_settlement_views.xml',
        # 'views/res_company_inherited_views.xml',
        "views/pf_gf_menus.xml",
    ],
    'installable': True,
}