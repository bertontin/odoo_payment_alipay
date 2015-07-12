# -*-coding: utf-8 -*-

{
    'name': 'Alipay Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer for Alipay',
    'version': '0.1',
    'description': """Alipay Payment Acquirer""",
    'author': 'Yang Ran',
    'depends': ['payment'],
    'data': [
        'views/alipay.xml',
        'views/payment_acquirer.xml',
        'data/alipay.xml',
    ],
    'installable': True,
}
