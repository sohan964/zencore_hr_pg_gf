{
    'name': 'Zencore Hr PF GF ',
    'version': "19.0.1.0.0",
    'author': "Sohan",
    'depends': ['sale', 'account', 'stock'],
    'data': [
        "security/ir.model.access.csv",
        "views/pf_policy_vesting_views.xml",
        "views/pf_policy_views.xml",
        "views/pf_gf_menus.xml",
    ],
    'installable': True,
}