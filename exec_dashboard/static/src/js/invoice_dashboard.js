/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class InvoiceExecDashboard extends Component {
    static template = "exec_dashboard.InvoiceDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            unpaid: { count: 0, amount: 0 },
            late: { count: 0, amount: 0 },
            paid: { count: 0, amount: 0 },
            sales: { count: 0, amount: 0 },
            purchases: { count: 0, amount: 0 },
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    today() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    firstDayOfMonth() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
    }

    get domains() {
        const base = [
            ["move_type", "=", "out_invoice"],
            ["state", "=", "posted"],
        ];
        return {
            unpaid: [...base, ["payment_state", "in", ["not_paid", "partial"]]],
            late: [
                ...base,
                ["payment_state", "in", ["not_paid", "partial"]],
                ["invoice_date_due", "<", this.today()],
            ],
            paid: [
                ...base,
                ["payment_state", "=", "paid"],
                ["invoice_date", ">=", this.firstDayOfMonth()],
            ],
        };
    }

    get saleDomain() {
        return [["state", "=", "sale"]];
    }

    get purchaseDomain() {
        return [["state", "in", ["purchase", "done"]]];
    }

    formatAmount(v) {
        return new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v || 0);
    }

    async loadData() {
        this.state.loading = true;
        const domains = this.domains;
        const measureByKey = {
            unpaid: "amount_residual",
            late: "amount_residual",
            paid: "amount_total",
        };
        const entries = Object.entries(domains);
        const results = await Promise.all(
            entries.map(([key, domain]) =>
                this.orm.searchRead("account.move", domain, [measureByKey[key]])
            )
        );
        entries.forEach(([key], i) => {
            const records = results[i];
            const field = measureByKey[key];
            this.state[key] = {
                count: records.length,
                amount: records.reduce((sum, r) => sum + (r[field] || 0), 0),
            };
        });

        let purchaseAvailable = true;
        const [saleRecords, purchaseRecords] = await Promise.all([
            this.orm.searchRead("sale.order", this.saleDomain, ["amount_total"]),
            this.orm
                .searchRead("purchase.order", this.purchaseDomain, ["amount_total"])
                .catch(() => {
                    purchaseAvailable = false;
                    return [];
                }),
        ]);
        this.state.sales = {
            count: saleRecords.length,
            amount: saleRecords.reduce((sum, r) => sum + (r.amount_total || 0), 0),
        };
        this.state.purchases = purchaseAvailable
            ? {
                  count: purchaseRecords.length,
                  amount: purchaseRecords.reduce((sum, r) => sum + (r.amount_total || 0), 0),
              }
            : null;

        this.state.loading = false;
    }

    openInvoices(key) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Invoices",
            res_model: "account.move",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: this.domains[key],
        });
    }

    openSales() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Sales Orders",
            res_model: "sale.order",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: this.saleDomain,
        });
    }

    openPurchases() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Purchase Orders",
            res_model: "purchase.order",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: this.purchaseDomain,
        });
    }
}

registry.category("actions").add("exec_dashboard.invoice_dashboard", InvoiceExecDashboard);
