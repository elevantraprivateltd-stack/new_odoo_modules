# -*- coding: utf-8 -*-
import io
import base64
from datetime import datetime, time

from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class StockStatusReportWizard(models.TransientModel):
    _name = 'stock.status.report.wizard'
    _description = 'Stock Status Report Wizard'

    date_from = fields.Date(
        string='From Date', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(
        string='To Date', required=True,
        default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        domain="[('company_id', '=', company_id)]",
        help='Leave empty to consider all warehouses / internal locations of the company.')
    category_id = fields.Many2one(
        'product.category', string='Product Category',
        help='Leave empty to consider all categories.')
    product_ids = fields.Many2many(
        'product.product', string='Products',
        help='Leave empty to include all products that had stock movement.')
    line_ids = fields.One2many(
        'stock.status.report.line', 'wizard_id', string='Report Lines')
    line_count = fields.Integer(compute='_compute_line_count')
    excel_file = fields.Binary(string='Excel File', readonly=True)
    excel_filename = fields.Char(string='Excel Filename', readonly=True)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_qty_field(self):
        """Return the correct 'done quantity' field name on stock.move,
        so the module keeps working across different Odoo versions
        (Odoo 17/18/19 use 'quantity', older versions used 'qty_done')."""
        move_fields = self.env['stock.move']._fields
        if 'quantity' in move_fields:
            return 'quantity'
        if 'qty_done' in move_fields:
            return 'qty_done'
        return 'product_qty'

    def _get_uom_field(self):
        """Return the correct UoM field name on stock.move. Odoo commonly
        calls it 'product_uom', some versions/customizations use
        'product_uom_id'. Detected at runtime so the module keeps working
        regardless of the exact Odoo version/customization."""
        move_fields = self.env['stock.move']._fields
        if 'product_uom' in move_fields:
            return 'product_uom'
        if 'product_uom_id' in move_fields:
            return 'product_uom_id'
        return False

    def _get_datetime_range(self):
        dt_from = datetime.combine(self.date_from, time.min)
        dt_to = datetime.combine(self.date_to, time.max)
        return dt_from, dt_to

    def _get_internal_location_ids(self):
        if self.warehouse_id:
            locations = self.env['stock.location'].search([
                ('id', 'child_of', self.warehouse_id.view_location_id.id),
                ('usage', '=', 'internal'),
            ])
        else:
            domain = [('usage', '=', 'internal')]
            if self.company_id:
                domain += ['|', ('company_id', '=', self.company_id.id),
                           ('company_id', '=', False)]
            locations = self.env['stock.location'].search(domain)
        return locations.ids

    def _get_products_to_report(self, location_ids):
        domain = []
        if self.product_ids:
            domain = [('id', 'in', self.product_ids.ids)]
        elif self.category_id:
            domain = [('categ_id', 'child_of', self.category_id.id)]

        if domain:
            return self.env['product.product'].search(domain)

        # No filter given: auto detect products that had any stock
        # movement touching the selected internal locations.
        move_domain = [
            ('state', '=', 'done'),
            '|',
            ('location_id', 'in', location_ids),
            ('location_dest_id', 'in', location_ids),
        ]
        groups = self.env['stock.move'].read_group(
            move_domain, ['product_id'], ['product_id'])
        product_ids = [g['product_id'][0] for g in groups if g.get('product_id')]
        if not product_ids:
            return self.env['product.product']
        return self.env['product.product'].browse(product_ids)

    def _aggregate_qty(self, domain, qty_field, product_uom_cache, uom_field=None):
        """Search stock.move with given domain and return {product_id: qty}
        converting every move quantity into the product's own Unit of
        Measure (moves can be recorded in a different, compatible UoM)."""
        res = {}
        read_fields = ['product_id', qty_field]
        if uom_field:
            read_fields.append(uom_field)
        moves = self.env['stock.move'].search_read(domain, read_fields)
        if not moves:
            return res

        product_ids = {m['product_id'][0] for m in moves if m.get('product_id')}
        # Warm up prefetch cache for uom_id in one query
        self.env['product.product'].browse(product_ids).mapped('uom_id')

        for m in moves:
            if not m.get('product_id'):
                continue
            pid = m['product_id'][0]
            qty = m.get(qty_field) or 0.0
            move_uom_id = False
            if uom_field and m.get(uom_field):
                move_uom_id = m[uom_field][0]

            if pid not in product_uom_cache:
                product_uom_cache[pid] = self.env['product.product'].browse(pid).uom_id

            product_uom = product_uom_cache[pid]
            if move_uom_id and product_uom and move_uom_id != product_uom.id:
                move_uom = self.env['uom.uom'].browse(move_uom_id)
                qty = move_uom._compute_quantity(qty, product_uom, round=False)

            res[pid] = res.get(pid, 0.0) + qty
        return res

    # ------------------------------------------------------------------
    # Main computation
    # ------------------------------------------------------------------
    def action_compute_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('"From Date" must be earlier than or equal to "To Date".'))

        self.line_ids.unlink()

        location_ids = self._get_internal_location_ids()
        if not location_ids:
            raise UserError(_(
                'No internal stock location was found for the selected '
                'Company / Warehouse.'))

        products = self._get_products_to_report(location_ids)
        if not products:
            return self._reopen_view()

        qty_field = self._get_qty_field()
        uom_field = self._get_uom_field()
        dt_from, dt_to = self._get_datetime_range()
        product_ids = products.ids
        base_domain = [
            ('state', '=', 'done'),
            ('product_id', 'in', product_ids),
        ]
        product_uom_cache = {}

        # --- Opening balance: net movement strictly BEFORE the period ---
        in_before = self._aggregate_qty(
            base_domain + [
                ('date', '<', dt_from),
                ('location_dest_id', 'in', location_ids),
                ('location_id', 'not in', location_ids),
            ], qty_field, product_uom_cache, uom_field)
        out_before = self._aggregate_qty(
            base_domain + [
                ('date', '<', dt_from),
                ('location_id', 'in', location_ids),
                ('location_dest_id', 'not in', location_ids),
            ], qty_field, product_uom_cache, uom_field)

        # --- All movement DURING the period (used for closing balance,
        #     so closing always equals real stock on hand even if there
        #     are other move types like inventory adjustments/MO/scrap) ---
        in_period_all = self._aggregate_qty(
            base_domain + [
                ('date', '>=', dt_from), ('date', '<=', dt_to),
                ('location_dest_id', 'in', location_ids),
                ('location_id', 'not in', location_ids),
            ], qty_field, product_uom_cache, uom_field)
        out_period_all = self._aggregate_qty(
            base_domain + [
                ('date', '>=', dt_from), ('date', '<=', dt_to),
                ('location_id', 'in', location_ids),
                ('location_dest_id', 'not in', location_ids),
            ], qty_field, product_uom_cache, uom_field)

        # --- The 4 specific requested columns ---
        received = self._aggregate_qty(
            base_domain + [
                ('date', '>=', dt_from), ('date', '<=', dt_to),
                ('location_dest_id', 'in', location_ids),
                ('location_id.usage', '=', 'supplier'),
            ], qty_field, product_uom_cache, uom_field)
        return_to_vendor = self._aggregate_qty(
            base_domain + [
                ('date', '>=', dt_from), ('date', '<=', dt_to),
                ('location_id', 'in', location_ids),
                ('location_dest_id.usage', '=', 'supplier'),
            ], qty_field, product_uom_cache, uom_field)
        sold = self._aggregate_qty(
            base_domain + [
                ('date', '>=', dt_from), ('date', '<=', dt_to),
                ('location_id', 'in', location_ids),
                ('location_dest_id.usage', '=', 'customer'),
            ], qty_field, product_uom_cache, uom_field)
        return_from_customer = self._aggregate_qty(
            base_domain + [
                ('date', '>=', dt_from), ('date', '<=', dt_to),
                ('location_dest_id', 'in', location_ids),
                ('location_id.usage', '=', 'customer'),
            ], qty_field, product_uom_cache, uom_field)

        vals_list = []
        for product in products:
            pid = product.id
            opening = in_before.get(pid, 0.0) - out_before.get(pid, 0.0)
            net_period = in_period_all.get(pid, 0.0) - out_period_all.get(pid, 0.0)
            closing = opening + net_period

            rec_qty = received.get(pid, 0.0)
            ret_v_qty = return_to_vendor.get(pid, 0.0)
            sold_qty = sold.get(pid, 0.0)
            ret_c_qty = return_from_customer.get(pid, 0.0)
            # Anything moved in/out during the period that was NOT to/from a
            # Vendor or a Customer location (e.g. Inventory Adjustments,
            # Manufacturing consumption/production, Scrap, internal
            # warehouse-to-warehouse transfers outside the selected
            # warehouse). Kept explicit so Opening + this table always
            # reconciles exactly to Closing.
            other_qty = net_period - (rec_qty - ret_v_qty - sold_qty + ret_c_qty)

            vals_list.append({
                'wizard_id': self.id,
                'product_id': pid,
                'product_code': product.default_code or '',
                'product_name': product.display_name,
                'uom_id': product.uom_id.id,
                'opening_qty': opening,
                'received_qty': rec_qty,
                'return_vendor_qty': ret_v_qty,
                'sold_qty': sold_qty,
                'return_customer_qty': ret_c_qty,
                'other_qty': other_qty,
                'closing_qty': closing,
            })

        self.env['stock.status.report.line'].create(vals_list)
        return self._reopen_view()

    def _reopen_view(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Status Report'),
            'res_model': 'stock.status.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # Print / Export
    # ------------------------------------------------------------------
    def action_print_pdf(self):
        self.ensure_one()
        if not self.line_ids:
            self.action_compute_report()
        return self.env.ref(
            'stock_status_report.action_report_stock_status'
        ).report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.line_ids:
            self.action_compute_report()

        if xlsxwriter is None:
            raise UserError(_(
                'The "xlsxwriter" python library is not installed on this '
                'server. Please ask your system administrator to run: '
                'pip install xlsxwriter'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(_('Stock Status'))

        title_fmt = workbook.add_format({'bold': True, 'font_size': 14})
        sub_fmt = workbook.add_format({'italic': True, 'font_size': 9, 'font_color': '#666666'})
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#D9E1F2', 'border': 1,
            'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
        })
        cell_fmt = workbook.add_format({'border': 1})
        num_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        bold_num_fmt = workbook.add_format(
            {'border': 1, 'num_format': '#,##0.00', 'bold': True})

        sheet.merge_range('A1:H1', _('Stock Status Report'), title_fmt)
        sheet.merge_range(
            'A2:H2',
            _('Period: %(f)s to %(t)s') % {'f': self.date_from, 't': self.date_to},
            sub_fmt)

        headers = [
            _('Product ID'), _('Product Name / Description'), _('UoM'),
            _('Opening Balance'), _('Received'), _('Return to Vendor'),
            _('Sold / Dispatched'), _('Return from Customer'),
            _('Other Adjustment'), _('Closing Balance'),
        ]
        row = 3
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_fmt)

        widths = [16, 40, 10, 14, 12, 14, 14, 16, 14, 14]
        for col, w in enumerate(widths):
            sheet.set_column(col, col, w)

        row += 1
        totals = {'opening': 0.0, 'received': 0.0, 'return_v': 0.0,
                  'sold': 0.0, 'return_c': 0.0, 'other': 0.0, 'closing': 0.0}
        for line in self.line_ids:
            sheet.write(row, 0, line.product_code, cell_fmt)
            sheet.write(row, 1, line.product_name, cell_fmt)
            sheet.write(row, 2, line.uom_id.name or '', cell_fmt)
            sheet.write_number(row, 3, line.opening_qty, num_fmt)
            sheet.write_number(row, 4, line.received_qty, num_fmt)
            sheet.write_number(row, 5, line.return_vendor_qty, num_fmt)
            sheet.write_number(row, 6, line.sold_qty, num_fmt)
            sheet.write_number(row, 7, line.return_customer_qty, num_fmt)
            sheet.write_number(row, 8, line.other_qty, num_fmt)
            sheet.write_number(row, 9, line.closing_qty, num_fmt)
            totals['opening'] += line.opening_qty
            totals['received'] += line.received_qty
            totals['return_v'] += line.return_vendor_qty
            totals['sold'] += line.sold_qty
            totals['return_c'] += line.return_customer_qty
            totals['other'] += line.other_qty
            totals['closing'] += line.closing_qty
            row += 1

        sheet.write(row, 0, '', cell_fmt)
        sheet.merge_range(row, 0, row, 2, _('Total'), header_fmt)
        sheet.write_number(row, 3, totals['opening'], bold_num_fmt)
        sheet.write_number(row, 4, totals['received'], bold_num_fmt)
        sheet.write_number(row, 5, totals['return_v'], bold_num_fmt)
        sheet.write_number(row, 6, totals['sold'], bold_num_fmt)
        sheet.write_number(row, 7, totals['return_c'], bold_num_fmt)
        sheet.write_number(row, 8, totals['other'], bold_num_fmt)
        sheet.write_number(row, 9, totals['closing'], bold_num_fmt)

        workbook.close()
        output.seek(0)

        self.excel_file = base64.b64encode(output.read())
        self.excel_filename = 'Stock_Status_Report_%s_%s.xlsx' % (
            self.date_from, self.date_to)

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=stock.status.report.wizard&id=%s&'
                   'field=excel_file&filename_field=excel_filename&download=true' % self.id,
            'target': 'self',
        }


class StockStatusReportLine(models.TransientModel):
    _name = 'stock.status.report.line'
    _description = 'Stock Status Report Line'
    _order = 'product_code, product_name'

    wizard_id = fields.Many2one(
        'stock.status.report.wizard', string='Report', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    product_code = fields.Char(string='Product ID / Reference')
    product_name = fields.Char(string='Product Name / Description')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    opening_qty = fields.Float(string='Opening Balance', digits='Product Unit of Measure')
    received_qty = fields.Float(string='Received', digits='Product Unit of Measure')
    return_vendor_qty = fields.Float(string='Return to Vendor', digits='Product Unit of Measure')
    sold_qty = fields.Float(string='Sold / Dispatched', digits='Product Unit of Measure')
    return_customer_qty = fields.Float(string='Return from Customer', digits='Product Unit of Measure')
    other_qty = fields.Float(
        string='Other Adjustment (Inventory/MO/Internal)',
        digits='Product Unit of Measure',
        help='Any other stock-in/out during the period that was not to/from '
             'a Vendor or Customer location: Inventory Adjustments, '
             'Manufacturing, Scrap, or transfers outside the selected '
             'Warehouse. Included so Opening + Received - Return to Vendor '
             '- Sold + Return from Customer + Other = Closing, always.')
    closing_qty = fields.Float(string='Closing Balance', digits='Product Unit of Measure')
