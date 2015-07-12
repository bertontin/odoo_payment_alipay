# -*- coding: utf-8 -*-

try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)

class AlipayController(http.Controller):
    _return_url = '/payment/alipay/return/'
    _notify_url = '/payment/alipay/notify/'

    def _get_return_url(self, **post):
        return_url = post.pop('return_url', '')
        ## paypal的实现里面，这里有一个兼容设计，调试的时候看看是否有必要
        return return_url

    @http.route(['/payment/alipay/return/',], type='http', auth='none')
    def alipay_return(self, **post):
        _logger.info('Beginning Alipay form_feedback with alipay_return: %s', pprint.pformat(post))
        request.registry['payment.transaction'].form_feedback(request.cr, SUPERUSER_ID, post, 'alipay', context=request.context)
        return_url = self._get_return_url(**post)
        return werkzeug.utils.redirect(return_url)

    @http.route(['/payment/alipay/notify/',], type='http', auth='none')
    def alipay_notify(self, **post):
        _logger.info('Beginning Alipay form_feedback with alipay_notify: %s', pprint.pformat(post))
        request.registry['payment.transaction'].form_feedback(request.cr, SUPERUSER_ID, post, 'alipay', context=request.context)
        return_url = self._get_return_url(**post)
        return werkzeug.utils.redirect(return_url)
