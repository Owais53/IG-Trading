from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


class Product(models.Model):
    _inherit = "product.template"

    model = fields.Char('Model')
    brand = fields.Char('Brand ')
    intransit_qty = fields.Float('Intransit Quantity',compute='get_intransit_qty')

    def get_qty(self):
        return True

    def get_intransit_qty(self):
        for rec in self:
            product_id = self.env['product.product'].search([('product_tmpl_id', '=', rec.id)]).id
            stock_move = self.env['stock.move'].search([('product_id', '=', product_id)])
            total_transit_qty = 0
            for line in stock_move:
             for picking in stock_move.picking_id:
              state = self.env['stock.picking'].search([('id','=',picking.id)])
              if state.state == 'intransit':
                intransit_qty = line.intransit_qty
                total_transit_qty += intransit_qty
                intransit_qty = 0
            rec.intransit_qty = total_transit_qty

class StockPicking(models.Model):
    _inherit = "stock.picking"

    check_validation = fields.Boolean(default=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('intransit','Intransit'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
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

class SaleOrderline(models.Model):
    _inherit = "sale.order.line"

    model = fields.Char('Model')
    brand = fields.Char('Brand ')
    sale_price = fields.Float('Previous Price')
    on_hand = fields.Float()
    others_qty = fields.Float('Others')
    provisional_factor = fields.Float('Provisional Factor')

    @api.onchange('model')
    def get_model(self):
        for rec in self:
            if rec.model:
                model = rec.model
                if model:
                 product = self.env['product.template'].search([('model', '=', rec.model)]).id
                 product_id = self.env['product.product'].search([('product_tmpl_id', '=', product)]).id
                 rec.product_id = product_id
                 rec.model = model

    @api.onchange('product_id')
    def get_product_id(self):
        for rec in self:
            if rec.product_id:
                product_id = rec.product_id
                # product = self.env['product.template'].search([('model', '=', rec.model)]).id
                product_id = self.env['product.product'].search([('id', '=', product_id.id)])
                rec.product_id = product_id
                rec.brand = product_id.brand
                rec.model = product_id.model
                if rec.product_id.categ_id.multiplier and float(rec.sale_price) > 0:
                    rec.provisional_factor = float(rec.sale_price) * float(rec.product_id.categ_id.multiplier)

    @api.onchange('product_id')
    def product_location_change(self):
        for rec in self:
            if rec.product_id:
                others = 0
                stock_qty_obj = self.env['stock.quant']
                stock_qty_lines = stock_qty_obj.search([('product_id', '=', rec.product_id.id)])
                if not stock_qty_lines:
                    rec.on_hand = 0
                    rec.others_qty = 0
                for stock in stock_qty_lines:
                    location_id = rec.order_id.warehouse_id.lot_stock_id
                    if location_id.id == stock.location_id.id:
                        rec.on_hand = stock.quantity
                    else:
                       if stock.quantity > 0:
                         others += stock.quantity
                         rec.others_qty = others




class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange('order_line')
    def get_sale_price(self):
        for rec in self:
            order = False
            if rec.partner_id:
                order = self.env['sale.order'].search(
                    [('partner_id', '=', rec.partner_id.id), ('state', '=', 'sale')],
                    order='id desc',
                    limit=1
                )
            else:
                rec.order_line.sale_price = 0
            if order:
                order_line = self.env['sale.order.line'].search_read([('order_id', '=', order.id)])
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
                    [('partner_id', '=', rec.partner_id.id), ('state', '=', 'purchase')],
                    order='id desc',
                    limit=1
                )
            else:
                rec.order_line.cost = 0
            if order:
                order_line = self.env['purchase.order.line'].search_read([('order_id', '=', order.id)])
                for currentline in rec.order_line:
                    for line in order_line:
                        if line['product_id'][0] == currentline.product_id.id:
                            currentline.cost = line['price_unit']

            else:
                rec.order_line.cost = 0

class ProductCategory(models.Model):
    _inherit = "product.category"

    multiplier = fields.Float('Multiplier')

class PurchaseOrderline(models.Model):
    _inherit = "purchase.order.line"

    model = fields.Char('Model')
    cost = fields.Char('Previous Cost')
    intransit_qty = fields.Float('Intransit Quantity',compute='get_intransit_qty')



    @api.onchange('model')
    def get_model(self):
        for rec in self:
            if rec.model:
                model = rec.model
                product = self.env['product.template'].search([('model', '=', rec.model)]).id
                product_id = self.env['product.product'].search([('product_tmpl_id', '=', product)]).id
                rec.product_id = product_id
                rec.model = model

    @api.depends('intransit_qty')
    def get_intransit_qty(self):
        for rec in self:
            if rec.product_id:
                intransit = 0
                rec.intransit_qty = 0
                stock_moves = self.env['stock.move'].search([('product_id', '=', rec.product_id.id)])
                for stock in stock_moves:
                 state = stock.picking_id.state
                 if state == "intransit":
                    intransit += stock.intransit_qty
                    rec.intransit_qty = intransit


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for rec in self:
            rec.state = 'done'
            for line in rec.move_ids_without_package:
                if line.intransit_qty > 0 and line.quantity_done == 0:
                    line.quantity_done = line.intransit_qty
                    line.intransit_qty = 0
                if line.intransit_qty > 0 and line.quantity_done > 0:
                    line.intransit_qty = line.intransit_qty - line.quantity_done
            return super(StockPicking, self).button_validate()


class AccountMove(models.Model):
    _inherit = "account.move"

    bilty = fields.Char()

    bilty_date = fields.Date(readonly=1, string='Bilty Date')
    no_packages = fields.Char('Number Of Packages')






class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    intransit_qty = fields.Float()
    
    
class deliveryreport(models.Model):
    _inherit = "stock.move"

    model = fields.Char('Model')
    brand = fields.Char('Brand ')
    on_hand = fields.Float(compute='product_location_change')
    others_qty = fields.Float('Others',compute='product_location_change')
    intransit_qty = fields.Float()

    @api.onchange('product_id')
    def product_location_change(self):
        for rec in self:
            if rec.product_id:
                others = 0
                stock_qty_obj = self.env['stock.quant']
                stock_qty_lines = stock_qty_obj.search([('product_id', '=', rec.product_id.id)])
                if not stock_qty_lines:
                    rec.on_hand = 0
                    rec.others_qty = 0
                for stock in stock_qty_lines:
                    sale_order = self.env['sale.order'].search([('name', '=', rec.origin)])
                    location_id = sale_order.warehouse_id.lot_stock_id
                    if location_id.id == stock.location_id.id:
                        rec.on_hand = stock.quantity
                        if rec.others_qty == 0:
                            rec.others_qty = 0
                    else:
                        if stock.quantity > 0:
                            others += stock.quantity
                            rec.others_qty = others
                            if rec.on_hand == 0:
                             rec.on_hand = 0

    @api.onchange('model')
    def get_model(self):
        for rec in self:
            if rec.model:
                model = rec.model
                if model:
                    product = self.env['product.template'].search([('model', '=', rec.model)]).id
                    product_id = self.env['product.product'].search([('product_tmpl_id', '=', product)]).id
                    rec.product_id = product_id
                    rec.model = model

    ############################### Product se brand or model uthaya hai #########################
    @api.onchange('product_id')
    def get_product_id(self):
        for rec in self:
            if rec.product_id:
                product_id = rec.product_id
                # product = self.env['product.template'].search([('model', '=', rec.model)]).id
                product_id = self.env['product.product'].search([('id', '=', product_id.id)])
                rec.product_id = product_id
                rec.brand = product_id.brand
                rec.model = product_id.model


class Delivery(models.Model):
    _inherit = "stock.picking"

    transport = fields.Char('Transport')



