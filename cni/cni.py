from openerp.osv import fields, osv
import datetime
import logging

_logger = logging.getLogger(__name__)

class product_template(osv.osv):
    _name = "product.template"
    _inherit = "product.template"
    _columns = {
        'sku': fields.char('SKU', size=64, required=True),
        'dimension': fields.char('Dimension', size=64, required=True),
    }
    
class asset_requisition(osv.osv):
    
    def send_request(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'Open'})
        return
    
    def _get_asset_state(self, cr, uid, team, internal_state):
        _logger.info("=in called method team========================================== : %r", team)
        _logger.info("=in called method internal_state========================================== : %r", internal_state)
        state_id = self.pool.get('asset.state').search(cr, uid, [('team','=',team),('name','=',internal_state)])
        if state_id:
            return state_id[0]
        else:
            return False
    
    def approve_request(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids[0], {'state':'Approved'})
        for f in self.browse(cr, uid, ids, context):
            #update status in sales lines
            line_ids = self.pool.get('asset.requisition.lines').search(cr, uid, [('requisition_id','=',f.id)])
            if line_ids:
                reconcile_rec = self.pool.get('asset.requisition.lines').browse(cr,uid,line_ids)
                _logger.info("=reconcile_rec========================================== : %r", reconcile_rec)
                for line in reconcile_rec:
                    #get wharhouse states
                    wh_state =  self.pool.get('asset.state').search(cr, uid, [('team','=',1),('name','=','Isuyusued')])
                    if wh_state:
                        _logger.info("=wh_state========================================== : %r", wh_state[0])
                        self.pool.get('asset.asset').write(cr,uid,line.name.id,{
                                                   'warehouse_state_id':wh_state[0],
                                                   'user_id':f.employee.id})
                    else:
                        _logger.info("=No appropriate state found e.g Issued")
        return
    
    def cancelled_request(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids[0], {'state':'Cancel'})
        return
    
    _name = "asset.requisition"
    _columns = {
        'name': fields.char('Name', size=64),
        'project':  fields.many2one('project.project', 'Project', required=True, ondelete='restrict'),
        'employee':  fields.many2one('hr.employee', 'Required By', required=True, ondelete='restrict'),
        'date_requisted':  fields.date('Date',required=True),
        'aprroved_by':  fields.many2one('res.users', 'Approved By'),
        'date_approved':  fields.date('Approved On'),
        'requisition_lines_ids': fields.one2many('asset.requisition.lines', 'requisition_id', 'Assets'),
        'note': fields.text('Any Note'),
        'state': fields.selection([('Draft','New'),
                                   ('Open','Waiting'),
                                   ('Approved','Approved'),
                                   ('Cancel', 'Cancelled'),
                                  ],
                                  'Status', required=True),
    }
    
    _defaults = {
                 'state':'Draft'
                 
    }
    
class asset_requisition_lines(osv.osv):
    """ Asset Requiston lines """
    
    def create(self, cr, uid, vals, context=None, check=True):
        result = super(osv.osv, self).create(cr, uid, vals, context)
        return result
  
     
    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        result = super(osv.osv, self).write(cr, uid, ids, vals, context)
        return result
     
    def unlink(self, cr, uid, ids, context=None):
        result = super(osv.osv, self).unlink(cr, uid, ids, context)
        return result 
    
    
    
    _name = 'asset.requisition.lines'
    _description = "This object store fee types"
    _columns = {
        'name': fields.many2one('asset.asset', 'Tool'),      
        'product_qty': fields.float('Quantity'),
        'requisition_id': fields.many2one('asset.requisition','Requisition'),
        'price_unit': fields.float('Unit Price'),
        'total':fields.float('Total'),
        
    }
    _sql_constraints = [  
        ('Fee Exisits', 'unique (name,requisition_id)', 'Resource Already exists')
    ] 
    _defaults = {
                 
    }
asset_requisition_lines()


class daily_sale_reconciliation(osv.osv):
    """This object store main business process of consumable products sale and its reconciliation"""
    
    def dispatch_product(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids[0], {'state':'Dispatched','dispatched_by':uid})
        #update lines state
        reconcile_ids = self.pool.get('sale.reconcile.lines').search(cr, uid, [('dispatch_id','=',ids[0])])
        
        if reconcile_ids:
            price = 0.0
            reconcile_rec = self.pool.get('sale.reconcile.lines').browse(cr,uid,reconcile_ids)
            for line in reconcile_rec:
                rec_product = self.pool.get('product.template').browse(cr,uid,line.name.product_tmpl_id.id)
                price = rec_product.list_price
                _logger.info("=price========================================== : %r", price)
                
                self.pool.get('sale.reconcile.lines').write(cr,uid,line.id,{'state':'Dispatched','price_unit':price,'total':float(line.dispatch_qty * price)})
        return
    
    def confirm_sale(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids[0], {'state':'Confirmed','confirmed_by':uid,'date_confirmed':datetime.date.today()})
    
        #update status in sales lines
        reconcile_ids = self.pool.get('sale.reconcile.lines').search(cr, uid, [('dispatch_id','=',ids[0])])
                
        if reconcile_ids:
            reconcile_rec = self.pool.get('sale.reconcile.lines').browse(cr,uid,reconcile_ids)
            for line in reconcile_rec:
                rec_product = self.pool.get('product.template').browse(cr,uid,line.name.product_tmpl_id.id)
                price = rec_product.list_price
                self.pool.get('sale.reconcile.lines').write(cr,uid,line.id,{'state':'Confirmed'})
                
        return
    
    def cancel_sale(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids[0], {'state':'Cancel','confirmed_by':uid})
        #update status in sales lines
        reconcile_ids = self.pool.get('sale.reconcile.lines').search(cr, uid, [('dispatch_id','=',ids[0])])
        if reconcile_ids:
            for prd_id in reconcile_ids:
                self.pool.get('sale.reconcile.lines').write(cr,uid,prd_id,{'state':'Cancel,',})
        return
    
    def _calculate_saleline_netsum(self, cr, uid, ids, name, args, context=None):
        result = {}
        sum = 0
        for f in self.browse(cr,uid,ids):
            reconcile_ids = self.pool.get('sale.reconcile.lines').search(cr, uid, [('dispatch_id','=',ids[0])])
            if reconcile_ids:
                rec_sale_lines = self.pool.get('sale.reconcile.lines').browse(cr, uid, reconcile_ids)
                for amount in rec_sale_lines:
                    sum = sum + amount.total
                result[f.id] = sum
        return result
    
    _name = "daily.sale.reconciliation"
    _columns = {
        'name': fields.char('Name', size=64),
        'project':  fields.many2one('project.project', 'Project', required=True, ondelete='restrict'),
        'employee':  fields.many2one('hr.employee', 'Technician', required=True, ondelete='restrict'),
        'date_dispatched':  fields.date('Date',required=True),
        'date_confirmed':  fields.date('Date Confirm',readonly=True),
        'dispatched_by':  fields.many2one('res.users', 'Dispatch By',readonly=True),
        'confirmed_by':  fields.many2one('res.users', 'Confirm By',readonly=True),
        'sale_reconcile_lines_ids': fields.one2many('sale.reconcile.lines', 'dispatch_id', 'Products'),
        'total_amount': fields.function(_calculate_saleline_netsum,string = 'Total Amount.',type = 'float',method = True),      
        'note': fields.text('Special Note'),
        'state': fields.selection([('Draft','New'),
                                   ('Dispatched','Open'),
                                   ('Confirmed','Confirmed'),
                                   ('Cancel', 'Cancel'),
                                  ],
                                  'Status', required=True),
    }
    
    _defaults = {
                 'state':'Draft'
                 
    }
    
class sale_reconcile_lines(osv.osv):
    """This object store main business process of consumable products sale and its reconciliationlines """
    
    def create(self, cr, uid, vals, context=None, check=True):
        result = super(osv.osv, self).create(cr, uid, vals, context)
        return result
  
     
    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        result = super(osv.osv, self).write(cr, uid, ids, vals, context)
        return result
     
    def onchange_returned_product(self, cr, uid, ids,return_qty):
        vals = {}
        for f in self.browse(cr,uid,ids):
            disp_qty = f.dispatch_qty
            price = f.price_unit
            net_amount = (disp_qty - return_qty)*price
            vals['total'] = net_amount
            vals['net_qty'] = disp_qty - return_qty
            update_lines = self.pool.get('sale.reconcile.lines').write(cr, uid, ids, {
                       'returned_qty':return_qty,
                       'net_qty':vals['net_qty'],
                       'total':vals['total'],
                       }) 
        return {'value':vals}
    
    def unlink(self, cr, uid, ids, context=None):
        result = super(osv.osv, self).unlink(cr, uid, ids, context)
        return result 
    
    _name = 'sale.reconcile.lines'
    _description = "This object store sale reconcile"
    _columns = {
        'name': fields.many2one('product.product', 'Product'),      
        'dispatch_qty': fields.float('Dispatched', required=True),
        'returned_qty': fields.float('Returned'),
        'net_qty': fields.float('Sold Out', readonly=True),
        'dispatch_id': fields.many2one('daily.sale.reconciliation','Sale Reconciliation'),
        'price_unit': fields.float('Unit Price'),
        'total':fields.float('Total'),
        'state': fields.selection([('Draft','New'),
                                   ('Dispatched','Open'),
                                   ('Confirmed','Confirmed'),
                                   ('Cancel', 'Cancel'),
                                  ],
                                  'Status', required=True),
        
    }
   
    _defaults = {'state':'Draft'}
sale_reconcile_lines()

#--------------------------------------- Clinets sotckable ----------------------------------------------------

class get_client_stock(osv.osv):
    
    def add_to_stock(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'Waiting'})
        return
    
    def get_transaction_no(self, cr, uid, team, internal_state):
        return False
    
    def confirm_add_to_stock(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'In_Stock'})
        return
    def stock_out(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'Waiting_Stockout'})
        return
    
    def confirm_stock_out(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'Waiting_Stockout'})
        return
    
    def cancelled_stock_reception(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids[0], {'state':'Cancel'})
        return
    
    def _calculate_stock_netsum(self, cr, uid, ids, name, args, context=None):
        result = {}
        sum = 0
        for f in self.browse(cr,uid,ids):
            reconcile_ids = self.pool.get('sale.reconcile.lines').search(cr, uid, [('dispatch_id','=',ids[0])])
            if reconcile_ids:
                rec_sale_lines = self.pool.get('sale.reconcile.lines').browse(cr, uid, reconcile_ids)
                for amount in rec_sale_lines:
                    sum = sum + amount.total
                result[f.id] = sum
        return result
    
    _name = "get.client.stock"
    _columns = {
        'name': fields.char('Name', size=64),
        'project':  fields.many2one('project.project', 'Project', required=True, ondelete='restrict'),
        'partner_id': fields.many2one('res.partner', 'Client'),
        'date_received':  fields.date('Date',required=True),
        'location_id': fields.many2one('stock.location', 'Warehouse', required=True, domain=[('usage','<>','view')]),
        'aprroved_by':  fields.many2one('res.users', 'Approved By' ,readonly = True),
        'stock_lines_ids': fields.one2many('client.stock.lines', 'stock_parent_id', 'Stock Lines'),
        'note': fields.text('Any Note'),
        'state': fields.selection([('Draft','New'),
                                   ('Waiting','Waiting'),
                                   ('In_Stock','In Stock'),
                                    ('Waiting_Stockout','Waiting Stockout'),
                                    ('Stockout','Stockout'),
                                   ('Cancel', 'Cancel'),
                                  ],
                                  'State', required=True),
    }
    
    _defaults = {
                 'state':'Draft'
                 
    }
    
class client_stock_lines(osv.osv):
    """ Clinets stock lines """
    
    def create(self, cr, uid, vals, context=None, check=True):
        result = super(osv.osv, self).create(cr, uid, vals, context)
        return result
  
     
    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        result = super(osv.osv, self).write(cr, uid, ids, vals, context)
        return result
     
    def unlink(self, cr, uid, ids, context=None):
        result = super(osv.osv, self).unlink(cr, uid, ids, context)
        return result 
    
    def onchange_returned_product(self, cr, uid, ids,return_qty):
        vals = {}
        for f in self.browse(cr,uid,ids):
            disp_qty = f.dispatch_qty
            vals['total'] = disp_qty *f.price
            update_lines = self.pool.get('client.stock.lines').write(cr, uid, ids, {
                       'net_qty':vals['net_qty'],
                       'total':vals['total'],
                       }) 
        return {'value':vals}
    
    _name = 'client.stock.lines'
    _description = "Clint stock lines"
    _columns = {
        'name': fields.many2one('product.product', 'Tool'),      
        'product_qty': fields.float('Quantity'),
        'stock_parent_id': fields.many2one('get.client.stock','Requisition'),
        'price_unit': fields.float('Unit Price'),
        'total':fields.float('Total'),
        
    }
   
    _defaults = {
                 
    }
client_stock_lines()
#-------------------------------------------------------------------------------------------------------------------------------

#----------------------------------- inherited project.project------------------------------------------------------------------

class project_project(osv.osv):
    """Extended project.project through inheritance"""
    _name = 'project.project'
    _inherit ='project.project'
    _columns = {
    'partner_id': fields.many2one('res.partner', 'Client'),
    'consumable': fields.one2many('daily.sale.reconciliation', 'project', 'Consumable'),
    'stockable': fields.one2many('get.client.stock', 'project', 'Stockable'),
    'tools_used': fields.one2many('asset.requisition', 'project', 'Tools'),
     
    }
    _defaults = {
    }
project_project()






   