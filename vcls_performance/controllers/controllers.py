# -*- coding: utf-8 -*-
from odoo import http

# class VclsPerformance(http.Controller):
#     @http.route('/vcls_performance/vcls_performance/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/vcls_performance/vcls_performance/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('vcls_performance.listing', {
#             'root': '/vcls_performance/vcls_performance',
#             'objects': http.request.env['vcls_performance.vcls_performance'].search([]),
#         })

#     @http.route('/vcls_performance/vcls_performance/objects/<model("vcls_performance.vcls_performance"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('vcls_performance.object', {
#             'object': obj
#         })