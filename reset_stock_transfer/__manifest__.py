{
    'name': 'Reset stock Transfer to draft',
    'version': '19.0.1.0.0',
    
    
    'depends': [
        "stock",
        "sale_management"
    ],

    'data': [
        "views/stock_picking_views.xml",
        "views/sale_order_views.xml"
    ],

    'installable': True,
    'application': False,
}