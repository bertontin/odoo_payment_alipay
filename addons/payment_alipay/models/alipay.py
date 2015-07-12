# -*- coding: utf-8 -*-

import logging
import hashlib
import pprint

from urllib import urlencode, urlopen
import urlparse
from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_alipay.controllers.main import AlipayController
from openerp.osv import osv, fields

_logger = logging.getLogger(__name__)

class AcquirerAlipay(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_alipay_urls(self):
        return {
            'alipay_form_url':'https://mapi.alipay.com/gateway.do?',
        }

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerAlipay, self)._get_providers(cr, uid, context=context)
        providers.append(['alipay', 'Alipay'])
        return providers

    _columns = {
        'alipay_partner': fields.char('Partner ID', required_if_provider='alipay'),
        'alipay_key': fields.char('Key', required_if_provider='alipay'),
        'alipay_seller_email': fields.char('Seller email'),
    }

    ## smart_str and params_filter was copy from https://github.com/fengli/alipay_python, Thanks.
    def _smart_str(self, s, encoding='utf-8', strings_only=False, errors='strict'):
        """ Return a bytestring version of  's', encoded as specified in 'encoding'.
        If strings_only is True, donot convert non-string-like objects."""
        if strings_only and isinstance(s, (types.NoneType, int)):
            return s
        if not isinstance(s, basestring):
            try:
                return str(s)
            except UnicodeEncodeError:
                if isinstance(s, Exception):
                    # An exception subclass containing non-ASCII data that doesnot
                    # know how to print itself properly. We shouldnot raise a further exception.
                    return ' '.join([self._smart_str(arg, encoding, strings_only, errors) for arg in s])
                return unicode(s).encode(encoding, errors)
        elif isinstance(s, unicode):
            return s.encode(encoding, errors)
        elif s and encoding != 'utf-8':
            return s.decode('utf-8', errors).encode(encoding, errors)
        else:
            return s

    def _params_filter(self, params):
        """对数组排序并除去数组中的空值和签名参数，返回数组和字符串"""
        _logger.info("alipay: before filter:%s", pprint.pformat(params))
        ks = params.keys()
        ks.sort()
        newparams = {}
        prestr = ''
        for k in ks:
            v = params[k]
            k = self._smart_str(k, 'utf-8')
            if k not in ('sign', 'sign_type') and v != '':
                newparams[k] = self._smart_str(v, 'utf-8')
                prestr += '%s=%s&' % (k, newparams[k])
        prestr = prestr[:-1]
        _logger.info("alipay:after filter:%s", pprint.pformat(params))
        _logger.info("alipay:prestr is: %s" % prestr)
        return newparams, prestr

    def _alipay_generate_md5_sign(self, acquirer, values):
        assert acquirer.provider == 'alipay'
        
        params, prestr = self._params_filter(values)

        return hashlib.md5(prestr + acquirer.alipay_key).hexdigest()

        

    def alipay_get_form_action_url(self, cr, uid, id, context=None):
        return self._get_alipay_urls()['alipay_form_url']

    ## 该函数参考https://github.com/fengli/alipay_python 实现，Thanks.
    def _alipay_verify_notify(self, acquirer, post):
        params = {}
        params['partner'] = acquirer.alipay_partner
        params['notify_id'] = post.get('notify_id')
        params['service'] = 'notify_verify'
        url = self._get_alipay_urls()['alipay_form_url']
        verify_result = urlopen(url, urlencode(params)).read()
        _logger.info("alipay: info of verify is %s %s", url, urlencode(params))
        _logger.info("alipay: return info of alipay_verify:%s", pprint.pformat(verify_result))
        if 'true' == verify_result.lower().strip():
            _logger.info("alipay: verify_notify successful with alipay.")
            return True
        _logger.info("alipay: verify_notify failed with alipay.")
        return False

    def alipay_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)

        _logger.info("alipay tx_values is :%s", pprint.pformat(tx_values))
        # alipay_tx_values = dict(tx_values)
        alipay_tx_values = {}
        alipay_tx_values.update({
            'service': 'create_partner_trade_by_buyer',
            'partner': acquirer.alipay_partner,
            'payment_type': '1',
            'notify_url': '%s' % urlparse.urljoin(base_url, AlipayController._notify_url),
            'return_url': '%s' % urlparse.urljoin(base_url, AlipayController._return_url),
            'seller_email': acquirer.alipay_seller_email,
            'out_trade_no': tx_values['reference'],
            'subject':'TBD', ## TODO
            'price': tx_values['amount'],
            'quantity': 1,
            'logistics_fee': '0.00',
            'logistics_type': 'EXPRESS',
            'logistics_payment': 'SELLER_PAY',
            'receive_name' : partner_values['first_name'] + partner_values['last_name'],
            'receive_address' : partner_values['address'],
            
            ## TODO

            ## 商品展示网址，暂时不处理
            ##'show_url': ,
            ## 防钓鱼功能，暂时不处理
            ##'anti_phishing_key': ,
            ##防钓鱼功能对应的客户端IP，暂不处理
            ##'exter_invoke_ip': ,
            '_input_charset': 'utf-8' ,
        })

        md5_sign = self._alipay_generate_md5_sign(acquirer, alipay_tx_values)
        alipay_tx_values.update({
            'sign_type': 'MD5',
            'sign': md5_sign,
            })

        for key, value in tx_values.items():
            if False == alipay_tx_values.has_key(key):
                alipay_tx_values[key] = value
        _logger.info("alipay alipay_tx_values is :%s", pprint.pformat(alipay_tx_values))

        return partner_values, alipay_tx_values

class TxAlipay(osv.Model):
    _inherit = 'payment.transaction'

    ## TODO which columns should be added?

    def _alipay_form_get_tx_from_data(self, cr, uid, data, context=None):
        reference = data.get('out_trade_no')
        if not reference:
            error_msg = 'Alipay: receive data with missing reference'
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference )], context=context)
        if not tx_ids or len(tx_ids)>1:
            error_msg = 'Alipay: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        tx = self.pool['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)

        return tx

    def _alipay_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []

        md5_sign = self.pool['payment.acquirer']._alipay_generate_md5_sign(tx.acquirer_id, data)
        if md5_sign != data.get('sign'):
            _logger.error("Alipay: Failed during MD5 check.")
            invalid_parameters.append(('md5_sign', data.get('sign'), md5_sign))
        verify_with_server = self.pool['payment.acquirer']._alipay_verify_notify(tx.acquirer_id, data)
        if False == verify_with_server:
            invalid_parameters.append(('verify_with_server', 'False', 'True'))

        return invalid_parameters

    def _alipay_form_validate(self, cr, uid, tx, data, context=None):
        status = data.get('trade_status')
        _logger.info("Alipay: status from alipay is %s", status)
        if status in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
            tx.write({'state': 'done',})
            return True
        else:
            tx.write({'state': 'error',})
            return False
