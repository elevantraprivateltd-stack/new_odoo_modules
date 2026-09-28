# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime

from odoo import fields, models


class ReportSalesTaxInvoice(models.AbstractModel):
    _name = 'report.sales_tax_invoice.report_sales_tax_invoice_template'
    _description = 'Sales Tax Invoice Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'get_report_data': self._get_report_data,
        }

    # ------------------------------------------------------------------
    # Generic helpers - intentionally avoid requiring extra custom fields.
    # When optional custom fields exist, they are used automatically.
    # ------------------------------------------------------------------
    def _first_attr(self, record, names, default=False):
        if not record:
            return default
        for name in names:
            if hasattr(record, name):
                value = getattr(record, name)
                if value not in (False, None, ''):
                    return value
        return default

    def _date_value(self, value):
        if not value:
            return False
        try:
            return value.date() if hasattr(value, 'date') else value
        except Exception:
            return value

    def _sale_orders(self, invoice):
        orders = invoice.invoice_line_ids.mapped('sale_line_ids.order_id')
        if not orders and invoice.invoice_origin:
            names = [x.strip() for x in invoice.invoice_origin.split(',') if x.strip()]
            orders = self.env['sale.order'].search([('name', 'in', names)])
        return orders

    def _pickings(self, invoice, orders):
        pickings = orders.mapped('picking_ids').filtered(lambda p: p.state == 'done')
        return pickings.sorted(key=lambda p: (p.date_done or p.scheduled_date or datetime.min))

    def _tax_breakdown(self, invoice):
        result = defaultdict(float)
        tax_rates = defaultdict(float)

        lines = invoice.invoice_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_note')
        )
        for line in lines:
            discounted_base = line.quantity * line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
            for tax in line.tax_ids:
                name = (tax.name or '').lower()
                rate = tax.amount if tax.amount_type == 'percent' else 0.0
                if tax.amount_type == 'percent':
                    amount = discounted_base * rate / 100.0
                elif tax.amount_type == 'fixed':
                    amount = tax.amount * line.quantity
                else:
                    # Division/group taxes are safely represented by the invoice's
                    # final amount_tax if they cannot be classified precisely here.
                    amount = 0.0

                if any(word in name for word in ('advance', 'withholding', 'wht')) or (0.0 < rate < 1.0):
                    key = 'advance'
                elif abs(rate - 1.0) < 0.0001:
                    key = 'sales_1'
                elif abs(rate - 4.0) < 0.0001:
                    key = 'sales_4'
                else:
                    key = 'other'

                result[key] += amount
                if rate:
                    tax_rates[key] = rate

        classified = result['advance'] + result['sales_1'] + result['sales_4'] + result['other']
        # Keep totals aligned with Odoo even when group/division taxes are present.
        if abs(classified - invoice.amount_tax) > 0.02:
            result['other'] += invoice.amount_tax - classified

        return {
            'advance_tax': result['advance'],
            'advance_rate': tax_rates['advance'],
            'sales_tax_1': result['sales_1'],
            'sales_tax_4': result['sales_4'],
            'other_tax': result['other'],
        }

    def _line_advance_tax(self, inv_line, qty):
        taxes = inv_line.tax_ids
        advance = taxes.filtered(
            lambda t: any(word in (t.name or '').lower() for word in ('advance', 'withholding', 'wht'))
        )
        if not advance:
            percentage_taxes = taxes.filtered(lambda t: t.amount_type == 'percent' and t.amount > 0)
            # The reference invoice uses the small per-line percentage as advance tax.
            advance = percentage_taxes.sorted('amount')[:1]

        if not advance:
            return 0.0, 0.0

        tax = advance[0]
        rate = tax.amount if tax.amount_type == 'percent' else 0.0
        base = qty * inv_line.price_unit * (1.0 - (inv_line.discount or 0.0) / 100.0)
        if tax.amount_type == 'percent':
            amount = base * rate / 100.0
        elif tax.amount_type == 'fixed':
            amount = tax.amount * qty
        else:
            amount = 0.0
        return rate, amount

    def _invoice_lines_with_batch(self, invoice):
        result = []
        for inv_line in invoice.invoice_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_note')
        ):
            sale_lines = inv_line.sale_line_ids
            moves = sale_lines.mapped('move_ids').filtered(lambda m: m.state == 'done')
            move_lines = moves.mapped('move_line_ids').filtered(lambda ml: ml.lot_id)

            if not move_lines:
                result.append(self._build_line_dict(inv_line, inv_line.quantity))
                continue

            for ml in move_lines:
                qty = self._first_attr(ml, ['quantity', 'qty_done'], 0.0) or 0.0
                uom = self._first_attr(ml, ['product_uom_id', 'product_uom'], False)
                result.append(self._build_line_dict(inv_line, qty, lot=ml.lot_id, uom=uom))
        return result

    def _build_line_dict(self, inv_line, qty, lot=False, uom=False):
        product = inv_line.product_id
        price_unit = inv_line.price_unit or 0.0
        discount = inv_line.discount or 0.0
        gross_amount = qty * price_unit
        after_discount = gross_amount * (1.0 - discount / 100.0)
        advance_rate, advance_amount = self._line_advance_tax(inv_line, qty)

        mfg_date = self._first_attr(
            lot,
            ['x_mfg_date', 'manufacturing_date', 'x_manufacturing_date', 'production_date'],
            False,
        ) if lot else False
        expiry_date = self._first_attr(
            lot,
            ['expiration_date', 'x_expiry_date', 'use_date'],
            False,
        ) if lot else False

        return {
            'product_code': product.default_code or '',
            'product_name': inv_line.name or product.display_name or '',
            'quantity': qty,
            'uom': (uom or inv_line.product_uom_id).name if (uom or inv_line.product_uom_id) else '',
            'batch_number': lot.name if lot else '',
            'mfg_date': self._date_value(mfg_date),
            'expiry_date': self._date_value(expiry_date),
            'price': price_unit,
            'discount': discount,
            'gross_amount': gross_amount,
            'after_discount': after_discount,
            'tax_percent': advance_rate,
            'tax_amount': advance_amount,
        }

    def _get_report_data(self, invoice):
        orders = self._sale_orders(invoice)
        pickings = self._pickings(invoice, orders)
        lines = self._invoice_lines_with_batch(invoice)
        tax_data = self._tax_breakdown(invoice)

        partner = invoice.partner_id
        company = invoice.company_id
        first_picking = pickings[:1]
        last_picking = pickings[-1:]

        delivery_date = self._date_value(
            self._first_attr(last_picking, ['date_done', 'scheduled_date'], False)
        ) or invoice.invoice_date
        dispatch_date = self._date_value(
            self._first_attr(first_picking, ['date_done', 'scheduled_date'], False)
        )

        sale_names = ', '.join(orders.mapped('name')) or (invoice.invoice_origin or '')
        picking_names = ', '.join(pickings.mapped('name'))
        remarks_parts = []
        if invoice.ref:
            remarks_parts.append(invoice.ref)
        if sale_names:
            remarks_parts.append('Based On Sales Orders %s.' % sale_names)
        if picking_names:
            remarks_parts.append('Based On Deliveries %s.' % picking_names)

        carton_count = self._first_attr(invoice, ['x_no_of_carton', 'x_carton_count'], 0) or 0
        courier_number = self._first_attr(invoice, ['x_courier_number', 'courier_number'], '') or ''
        courier_name = self._first_attr(invoice, ['x_courier_name', 'courier_name'], '') or ''
        region_city = self._first_attr(partner, ['city', 'state_id'], '')
        if hasattr(region_city, 'name'):
            region_city = region_city.name

        customer_ntn = self._first_attr(partner, ['vat', 'company_registry'], '') or ''
        company_strn = self._first_attr(
            company,
            ['company_registry', 'l10n_pk_strn', 'x_strn'],
            '',
        ) or ''

        # Prefer the invoice user; otherwise show the creator in Prepared By.
        prepared_user = invoice.invoice_user_id or invoice.create_uid
        audited_user = invoice.write_uid if invoice.write_uid != prepared_user else False

        print_dt = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        print_time = print_dt.strftime('%I:%M:%S%p').lstrip('0')
        invoice_number = self._first_attr(
            invoice,
            ['x_sap_document', 'x_sap_document_no', 'x_document_number', 'x_invoice_number'],
            invoice.name or '',
        )
        customer_address = ', '.join([x for x in [partner.street, partner.street2, partner.city] if x])
        company_address = ', '.join([x for x in [company.street, company.street2, company.city, company.state_id.name if company.state_id else '', company.country_id.name if company.country_id else ''] if x])
        warranty_person = self._first_attr(company, ['x_warranty_person', 'x_authorized_person'], '') or (prepared_user.name if prepared_user else '')
        discount_base = sum(x['gross_amount'] for x in lines)
        discount_amount = sum(x['gross_amount'] - x['after_discount'] for x in lines)

        result = {
            'print_datetime': print_dt,
            'print_datetime_str': '%s / %s' % (print_dt.strftime('%m/%d/%Y'), print_time),
            'invoice_number': invoice_number,
            'lines': lines,
            'qty_total': sum(x['quantity'] for x in lines),
            'gross_total': sum(x['after_discount'] for x in lines),
            'discount_amount': discount_amount,
            'discount_percent': (discount_amount / discount_base * 100.0) if discount_base else 0.0,
            'delivery_date': delivery_date,
            'dispatch_date': dispatch_date,
            'customer_code': partner.ref or '',
            'customer_address': customer_address,
            'customer_ntn': customer_ntn,
            'region_city': region_city or '',
            'customer_ref': invoice.ref or invoice.payment_reference or '',
            'carton_count': carton_count,
            'courier_number': courier_number,
            'courier_name': courier_name,
            'remarks': ' '.join(remarks_parts),
            'company_ntn': company.vat or '',
            'company_strn': company_strn,
            'company_address': company_address,
            'warranty_person': warranty_person,
            'prepared_by': prepared_user.name if prepared_user else '',
            'prepared_date': invoice.create_date,
            'prepared_date_str': fields.Datetime.context_timestamp(self, invoice.create_date).strftime('%d-%b-%y') if invoice.create_date else '',
            'audited_by': audited_user.name if audited_user else '',
            'audited_date': invoice.write_date if audited_user else False,
            'audited_date_str': fields.Datetime.context_timestamp(self, invoice.write_date).strftime('%d-%b-%y %H:%M') if (audited_user and invoice.write_date) else '',
        }
        result.update(tax_data)
        return result
