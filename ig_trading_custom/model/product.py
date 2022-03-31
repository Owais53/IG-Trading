from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


class Product(models.Model):
    _inherit = "product.template"

    model = fields.Char('Model')
    intransit_qty = fields.Float(compute='get_intransit_qty')

    def get_qty(self):
        return True

    def get_intransit_qty(self):
        for rec in self:
            product_id = self.env['product.product'].search([('product_tmpl_id', '=', rec.id)]).id
            stock_move = self.env['stock.move'].search([('product_id', '=', product_id)])
            total_transit_qty = 0
            for line in stock_move:
                intransit_qty = line.intransit_qty
                total_transit_qty += intransit_qty
                intransit_qty = 0
            rec.intransit_qty = total_transit_qty


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

    @api.onchange('product_id')
    def show_on_hand_quantity(self):
        for rec in self:
            if rec.product_id:
                model = rec.model
                product = self.env['product.template'].search([('model', '=', rec.model)]).id
                product_id = self.env['product.product'].search([('product_tmpl_id', '=', product)]).id
                rec.product_id = product_id
                rec.model = model


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange('order_line')
    def get_sale_price(self):
        for rec in self:
            order = False
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
            order = False
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
    intransit_qty = fields.Float()

    @api.onchange('model')
    def get_model(self):
        for rec in self:
            if rec.model:
                model = rec.model
                product = self.env['product.template'].search([('model', '=', rec.model)]).id
                product_id = self.env['product.product'].search([('product_tmpl_id', '=', product)]).id
                rec.product_id = product_id
                rec.model = model

    @api.onchange('product_id')
    def show_intransit_quantity(self):
        for rec in self:
            if rec.product_id:
                intransit = 0
                stock_moves = self.env['stock.move'].search([('product_id','=',rec.product_id.id)])
                for move in stock_moves:
                 state = move.picking_id.state
                 if state == "intransit":
                  intransit += move.intransit_qty
                  rec.intransit_qty = intransit



class StockMove(models.Model):
    _inherit = 'stock.move'

    intransit_qty = fields.Float(string="Intransit Quantity")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    check_validation = fields.Boolean(default=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('intransit', 'Intransit'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")

    def before_validation(self):
        self.state = 'intransit'
        self.check_validation = True
        return True
