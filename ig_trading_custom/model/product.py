from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


class Product(models.Model):
    _inherit = "product.template"

    model = fields.Char('Model')



class SaleOrderline(models.Model):
    _inherit = "sale.order.line"

    model = fields.Char('Model')
    sale_price = fields.Float('Previous Price')
    on_hand = fields.Integer()


    @api.onchange('model')
    def get_model(self):
       for rec in self:
        if rec.model:
         model = rec.model
         product = self.env['product.template'].search([('model','=',rec.model)]).id
         product_id = self.env['product.product'].search([('product_tmpl_id','=',product)]).id
         rec.product_id = product_id
         rec.model = model





class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange('order_line')
    def get_sale_price(self):
        for rec in self:
            if rec.partner_id:
                order = self.env['sale.order'].search(
                    [('partner_id', '=', rec.partner_id.id),('state','=','sale')],
                    order='id desc',
                    limit=1
                )
            else:
                rec.order_line.sale_price = 0
            if order:
                order_line = self.env['sale.order.line'].search_read([('order_id','=',order.id)])
                for currentline in rec.order_line:
                 for line in order_line:
                     if line['product_id'][0] == currentline.product_id.id:
                         currentline.sale_price = line['price_unit']

            else:
                rec.order_line.sale_price = 0

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.onchange('order_line')
    def get_cost(self):
        for rec in self:
            if rec.partner_id:
                order = self.env['purchase.order'].search(
                    [('partner_id', '=', rec.partner_id.id),('state','=','purchase')],
                    order='id desc',
                    limit=1
                )
            else:
                rec.order_line.cost = 0
            if order:
                order_line = self.env['purchase.order.line'].search_read([('order_id','=',order.id)])
                for currentline in rec.order_line:
                 for line in order_line:
                     if line['product_id'][0] == currentline.product_id.id:
                         currentline.cost = line['price_unit']

            else:
                rec.order_line.cost = 0



class PurchaseOrderline(models.Model):
    _inherit = "purchase.order.line"

    model = fields.Char('Model')
    cost = fields.Char('Cost')

    @api.onchange('model')
    def get_model(self):
        for rec in self:
            if rec.model:
                model = rec.model
                product = self.env['product.template'].search([('model', '=', rec.model)]).id
                product_id = self.env['product.product'].search([('product_tmpl_id', '=', product)]).id
                rec.product_id = product_id
                rec.model = model





