{
    'name' : 'Ig Trading Custom',
    'version' : '1.1',
    'summary': '',
    'sequence': 10,
    'description': """This Module will add functionality to Product,Sales Order and Purchase Order.
    """,
    'category': '',
    'website': '',
    'images' : [],
    'depends' : ['product','sale'],
    'data': [
         'security/ir.model.access.csv',
        'view/product.xml',
         'report/report_view.xml',
        'report/sale_order.xml',
        'report/packing_list.xml',
    ],
    'demo': [

    ],
    'qweb': [

    ],
    'installable': True,
    'application': True,
    'auto_install': False,

}
