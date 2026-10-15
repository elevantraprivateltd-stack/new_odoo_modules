from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CompanyDuplicateWizard(models.TransientModel):
    _name = "company.duplicate.wizard"
    _description = "Company Master Data Clone"

    # =========================================================
    # WIZARD FIELDS
    # =========================================================
    source_company_id = fields.Many2one(
        "res.company",
        string="Source Company",
        required=True,
    )
    new_company_name = fields.Char(
        string="New Company Name",
        required=True,
    )
    copy_partners = fields.Boolean(
        string="Customers / Vendors",
        default=False,  # ← default OFF kar diya
        help="Copy contacts linked to the source company.",
    )
    copy_accounting = fields.Boolean(
        string="Chart of Accounts & Accounting Setup",
        default=True,
        help=(
            "Copy accounting settings, chart of accounts, "
            "account groups, tax groups, taxes, journals "
            "(setup only, no journal entries), payment terms "
            "and fiscal positions."
        ),
    )
    copy_warehouses = fields.Boolean(
        string="Warehouses & Locations",
        default=True,
        help=(
            "Copy the warehouse and internal location setup "
            "(structure only - no stock quantities or stock "
            "moves)."
        ),
    )

    # =========================================================
    # ONCHANGE
    # =========================================================
    @api.onchange("source_company_id")
    def _onchange_source_company_id(self):
        if self.source_company_id:
            self.new_company_name = self.source_company_id.name + " - Copy"

    # =========================================================
    # MAIN ACTION
    # =========================================================
    def action_duplicate(self):
        self.ensure_one()
        if not self.source_company_id:
            raise UserError(_("Please select the source company."))
        if not self.new_company_name:
            raise UserError(_("Please enter the new company name."))

        Company = self.env["res.company"].sudo()

        if Company.search([("name", "=", self.new_company_name)], limit=1):
            raise UserError(_("A company with this name already exists."))

        source = self.source_company_id.sudo()
        target = self._create_target_company(source, Company)

        mapping = {
            "res.partner": {},
            "account.group": {},
            "account.account": {},
            "account.tax.group": {},
            "account.tax": {},
            "account.journal": {},
            "account.fiscal.position": {},
            "account.payment.term": {},
            "stock.location": {},
            "stock.warehouse": {},
        }

        # Partners (only if checked)
        if self.copy_partners:
            self._copy_partners(source, target, mapping)

        # Products → permanently removed (never copy)

        # Accounting
        if self.copy_accounting:
            self._copy_account_groups(source, target, mapping)
            self._copy_accounts(source, target, mapping)
            self._copy_tax_groups(source, target, mapping)
            self._copy_taxes(source, target, mapping)
            self._copy_journals(source, target, mapping)
            self._copy_payment_terms(source, target, mapping)
            self._copy_fiscal_positions(source, target, mapping)
            self._apply_accounting_settings(source, target, mapping)

        # Warehouses
        if self.copy_warehouses:
            self._copy_locations(source, target, mapping)
            self._copy_warehouses(source, target, mapping)

        return {
            "type": "ir.actions.act_window",
            "name": _("New Company"),
            "res_model": "res.company",
            "res_id": target.id,
            "view_mode": "form",
            "target": "current",
        }

    # =========================================================
    # COMPANY CREATE
    # =========================================================
    def _create_target_company(self, source, Company):
        company_vals = {
            "name": self.new_company_name,
        }

        if source.currency_id and "currency_id" in Company._fields:
            company_vals["currency_id"] = source.currency_id.id

        simple_fields = [
            "street", "street2", "city", "zip", "state_id", "country_id",
            "phone", "mobile", "email", "website", "vat",
            "company_registry", "paperformat_id",
        ]
        settings_fields = [
            "account_fiscal_country_id", "anglo_saxon_accounting",
            "tax_calculation_rounding_method", "tax_exigibility",
            "fiscalyear_last_day", "fiscalyear_last_month",
            "bank_account_code_prefix", "cash_account_code_prefix",
            "transfer_account_code_prefix",
        ]

        for field_name in simple_fields + settings_fields:
            if field_name not in Company._fields:
                continue
            field = Company._fields[field_name]
            if field.compute:
                continue
            value = source[field_name]
            if hasattr(value, "id"):
                if value:
                    company_vals[field_name] = value.id
            else:
                company_vals[field_name] = value

        return Company.create(company_vals)

    def _apply_accounting_settings(self, source, target, mapping):
        Company = self.env["res.company"].sudo()
        account_mapping = mapping.get("account.account", {})
        vals = {}

        if "transfer_account_id" in Company._fields and source.transfer_account_id:
            new_account_id = account_mapping.get(source.transfer_account_id.id)
            if new_account_id:
                vals["transfer_account_id"] = new_account_id

        if vals:
            target.write(vals)

    # =========================================================
    # PARTNERS
    # =========================================================
    def _copy_partners(self, source, target, mapping):
        Partner = self.env["res.partner"].sudo()
        partners = Partner.search([("company_id", "=", source.id)])
        mapping.setdefault("res.partner", {})

        simple_fields = [
            "name", "company_type", "type", "street", "street2", "city", "zip",
            "phone", "email", "website", "vat", "function", "comment", "lang",
        ]

        for partner in partners:
            if partner.id in mapping["res.partner"]:
                continue

            vals = {}
            for field_name in simple_fields:
                if field_name in Partner._fields:
                    field = Partner._fields[field_name]
                    if field.compute:
                        continue
                    vals[field_name] = partner[field_name]

            if "company_id" in Partner._fields:
                vals["company_id"] = target.id
            if "country_id" in Partner._fields and partner.country_id:
                vals["country_id"] = partner.country_id.id
            if "state_id" in Partner._fields and partner.state_id:
                vals["state_id"] = partner.state_id.id
            if "customer_rank" in Partner._fields:
                vals["customer_rank"] = partner.customer_rank
            if "supplier_rank" in Partner._fields:
                vals["supplier_rank"] = partner.supplier_rank

            new_partner = Partner.create(vals)
            mapping["res.partner"][partner.id] = new_partner.id

    # =========================================================
    # ACCOUNT GROUPS
    # =========================================================
    def _copy_account_groups(self, source, target, mapping):
        Group = self.env["account.group"].sudo()
        groups = Group.search([("company_id", "=", source.id)])
        groups = groups.sorted(key=lambda x: len(x.parent_path or ""))

        for group in groups:
            vals = {
                "name": group.name,
                "company_id": target.id,
            }
            if "code_prefix_start" in Group._fields:
                vals["code_prefix_start"] = group.code_prefix_start
            if "code_prefix_end" in Group._fields:
                vals["code_prefix_end"] = group.code_prefix_end
            if "parent_id" in Group._fields:
                parent_id = mapping["account.group"].get(group.parent_id.id)
                if parent_id:
                    vals["parent_id"] = parent_id

            new_group = Group.create(vals)
            mapping["account.group"][group.id] = new_group.id

    # =========================================================
    # ACCOUNTS
    # =========================================================
    def _copy_accounts(self, source, target, mapping):
        Account = self.env["account.account"].sudo()
        account_mapping = mapping.setdefault("account.account", {})

        source_accounts = Account.search([("company_ids", "in", [source.id])])
        target_accounts = Account.search([("company_ids", "in", [target.id])])
        target_by_code = {acc.code: acc for acc in target_accounts if acc.code}

        for source_account in source_accounts:
            code = source_account.code
            if not code or source_account.id in account_mapping:
                continue

            target_account = target_by_code.get(code)
            if not target_account:
                target_account = Account.search([
                    ("code", "=", code),
                    ("company_ids", "in", [target.id]),
                ], limit=1)

            if target_account:
                account_mapping[source_account.id] = target_account.id
                target_by_code[code] = target_account
                continue

            # Share the account with new company
            source_account.write({"company_ids": [(4, target.id)]})
            source_account.with_company(target.id).write({"code": code})

            target_by_code[code] = source_account
            account_mapping[source_account.id] = source_account.id

    # =========================================================
    # TAX GROUPS
    # =========================================================
    def _copy_tax_groups(self, source, target, mapping):
        TaxGroup = self.env["account.tax.group"].sudo()
        groups = TaxGroup.search([("company_id", "=", source.id)])

        for group in groups:
            existing = TaxGroup.search([
                ("company_id", "=", target.id),
                ("name", "=", group.name),
            ], limit=1)
            if existing:
                mapping["account.tax.group"][group.id] = existing.id
                continue

            vals = {
                "name": group.name,
                "company_id": target.id,
            }
            if "sequence" in TaxGroup._fields:
                vals["sequence"] = group.sequence
            if "country_id" in TaxGroup._fields and group.country_id:
                vals["country_id"] = group.country_id.id

            new_group = TaxGroup.create(vals)
            mapping["account.tax.group"][group.id] = new_group.id

    # =========================================================
    # TAXES
    # =========================================================
    def _copy_taxes(self, source, target, mapping):
        Tax = self.env["account.tax"].sudo()
        taxes = Tax.search([("company_id", "=", source.id)])

        for tax in taxes:
            existing = Tax.search([
                ("company_id", "=", target.id),
                ("name", "=", tax.name),
                ("type_tax_use", "=", tax.type_tax_use),
            ], limit=1)
            if existing:
                mapping["account.tax"][tax.id] = existing.id
                continue

            vals = {}
            fields_to_copy = [
                "name", "type_tax_use", "amount_type", "amount",
                "description", "sequence", "active",
                "price_include", "include_base_amount",
            ]
            for field_name in fields_to_copy:
                if field_name in Tax._fields and not Tax._fields[field_name].compute:
                    vals[field_name] = tax[field_name]

            vals["company_id"] = target.id

            if "country_id" in Tax._fields:
                target_country = target.account_fiscal_country_id or target.country_id
                if target_country:
                    vals["country_id"] = target_country.id
                elif tax.country_id:
                    vals["country_id"] = tax.country_id.id

            if tax.tax_group_id:
                new_group_id = mapping["account.tax.group"].get(tax.tax_group_id.id)
                if new_group_id:
                    vals["tax_group_id"] = new_group_id

            if "invoice_label" in Tax._fields:
                vals["invoice_label"] = tax.invoice_label
            if "tax_scope" in Tax._fields:
                vals["tax_scope"] = tax.tax_scope

            new_tax = Tax.create(vals)
            mapping["account.tax"][tax.id] = new_tax.id

    # =========================================================
    # JOURNALS
    # =========================================================
    def _copy_journals(self, source, target, mapping):
        Journal = self.env["account.journal"].sudo()
        journals = Journal.search([("company_id", "=", source.id)])
        account_mapping = mapping.get("account.account", {})

        for journal in journals:
            existing = Journal.search([
                ("company_id", "=", target.id),
                ("code", "=", journal.code),
            ], limit=1)
            if existing:
                mapping["account.journal"][journal.id] = existing.id
                continue

            vals = {
                "name": journal.name,
                "type": journal.type,
                "code": journal.code,
                "company_id": target.id,
            }

            if journal.default_account_id:
                account_id = account_mapping.get(journal.default_account_id.id)
                if account_id:
                    vals["default_account_id"] = account_id

            if "suspense_account_id" in Journal._fields and journal.suspense_account_id:
                account_id = account_mapping.get(journal.suspense_account_id.id)
                if account_id:
                    vals["suspense_account_id"] = account_id

            new_journal = Journal.create(vals)
            mapping["account.journal"][journal.id] = new_journal.id

    # =========================================================
    # PAYMENT TERMS
    # =========================================================
    def _copy_payment_terms(self, source, target, mapping):
        PaymentTerm = self.env["account.payment.term"].sudo()
        terms = PaymentTerm.search([])

        for term in terms:
            existing = PaymentTerm.search([("name", "=", term.name)], limit=1)
            if existing:
                mapping["account.payment.term"][term.id] = existing.id
                continue

            vals = {"name": term.name}
            if "note" in PaymentTerm._fields:
                vals["note"] = term.note

            new_term = PaymentTerm.create(vals)
            mapping["account.payment.term"][term.id] = new_term.id

    # =========================================================
    # FISCAL POSITIONS
    # =========================================================
    def _copy_fiscal_positions(self, source, target, mapping):
        FiscalPosition = self.env["account.fiscal.position"].sudo()
        positions = FiscalPosition.search([("company_id", "=", source.id)])

        for position in positions:
            vals = {
                "name": position.name,
                "company_id": target.id,
            }
            for field_name in ["auto_apply", "sequence", "foreign_vat"]:
                if field_name in FiscalPosition._fields:
                    vals[field_name] = position[field_name]

            new_position = FiscalPosition.create(vals)
            mapping["account.fiscal.position"][position.id] = new_position.id

    # =========================================================
    # LOCATIONS
    # =========================================================
    def _copy_locations(self, source, target, mapping):
        Location = self.env["stock.location"].sudo()
        location_mapping = mapping.setdefault("stock.location", {})

        source_locations = Location.search([("company_id", "=", source.id)])
        source_locations = source_locations.sorted(key=lambda x: len(x.parent_path or ""))

        target_locations = Location.search([("company_id", "=", target.id)])
        target_by_name = {loc.name: loc for loc in target_locations}

        for location in source_locations:
            if location.id in location_mapping:
                continue

            existing = target_by_name.get(location.name)
            if existing:
                location_mapping[location.id] = existing.id
                continue

            vals = {
                "name": location.name,
                "usage": location.usage,
                "company_id": target.id,
            }
            if "active" in Location._fields:
                vals["active"] = location.active

            parent_id = location_mapping.get(location.location_id.id)
            if parent_id:
                vals["location_id"] = parent_id

            new_location = Location.create(vals)
            target_by_name[location.name] = new_location
            location_mapping[location.id] = new_location.id

    # =========================================================
    # WAREHOUSES
    # =========================================================
    def _copy_warehouses(self, source, target, mapping):
        Warehouse = self.env["stock.warehouse"].sudo()
        warehouse_mapping = mapping.setdefault("stock.warehouse", {})

        source_warehouses = Warehouse.search([("company_id", "=", source.id)])
        target_warehouses = Warehouse.search([("company_id", "=", target.id)])

        target_by_name = {wh.name: wh for wh in target_warehouses}
        target_by_code = {wh.code: wh for wh in target_warehouses}

        for warehouse in source_warehouses:
            if warehouse.id in warehouse_mapping:
                continue

            existing = target_by_name.get(warehouse.name) or target_by_code.get(warehouse.code)
            if existing:
                warehouse_mapping[warehouse.id] = existing.id
                continue

            code = self._unique_warehouse_code(Warehouse, warehouse.code)

            vals = {
                "name": warehouse.name,
                "code": code,
                "company_id": target.id,
            }

            if "partner_id" in Warehouse._fields and warehouse.partner_id:
                partner_id = mapping.get("res.partner", {}).get(warehouse.partner_id.id)
                if partner_id:
                    vals["partner_id"] = partner_id

            new_warehouse = Warehouse.create(vals)
            target_by_name[warehouse.name] = new_warehouse
            target_by_code[code] = new_warehouse
            warehouse_mapping[warehouse.id] = new_warehouse.id

    @staticmethod
    def _unique_warehouse_code(Warehouse, base_code):
        base_code = (base_code or "WH")[:5]
        if not Warehouse.search([("code", "=", base_code)], limit=1):
            return base_code

        prefix = base_code[:3] or "WH"
        suffix = 1
        while True:
            candidate = (prefix + str(suffix))[:5]
            if not Warehouse.search([("code", "=", candidate)], limit=1):
                return candidate
            suffix += 1
