/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SaleExecDashboard extends Component {
    static template = "exec_dashboard.SaleDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            draft: { count: 0, amount: 0 },
            sent: { count: 0, amount: 0 },
            confirmed: { count: 0, amount: 0 },
            invoiceDue: { count: 0, amount: 0 },
            open: { count: 0, amount: 0 },
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    get domains() {
        return {
            draft: [["state", "=", "draft"]],
            sent: [["state", "=", "sent"]],
            confirmed: [["state", "=", "sale"]],
            invoiceDue: [["invoice_status", "=", "to invoice"]],
            open: [["state", "in", ["draft", "sent"]]],
        };
    }

    formatAmount(v) {
        return new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v || 0);
    }

    async loadData() {
        this.state.loading = true;
        const domains = this.domains;
        const entries = Object.entries(domains);
        const results = await Promise.all(
            entries.map(([, domain]) =>
                this.orm.searchRead("sale.order", domain, ["amount_total"])
            )
        );
        entries.forEach(([key], i) => {
            const records = results[i];
            this.state[key] = {
                count: records.length,
                amount: records.reduce((sum, r) => sum + (r.amount_total || 0), 0),
            };
        });
        this.state.loading = false;
    }

    openOrders(key) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Sales Orders",
            res_model: "sale.order",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: this.domains[key],
        });
    }
}

registry.category("actions").add("exec_dashboard.sale_dashboard", SaleExecDashboard);
