/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CrmExecDashboard extends Component {
    static template = "exec_dashboard.CrmDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            total: 0,
            newLeads: 0,
            inProgress: 0,
            won: 0,
            lost: 0,
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    firstDayOfMonth() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
    }

    get domains() {
        return {
            total: [["type", "=", "opportunity"]],
            newLeads: [
                ["type", "=", "opportunity"],
                ["create_date", ">=", this.firstDayOfMonth()],
            ],
            inProgress: [
                ["type", "=", "opportunity"],
                ["active", "=", true],
                ["stage_id.is_won", "=", false],
            ],
            won: [
                ["type", "=", "opportunity"],
                ["stage_id.is_won", "=", true],
            ],
            lost: [
                ["type", "=", "opportunity"],
                ["active", "=", false],
                ["probability", "=", 0],
            ],
        };
    }

    async loadData() {
        this.state.loading = true;
        const domains = this.domains;
        const entries = Object.entries(domains);
        const results = await Promise.all(
            entries.map(([, domain]) =>
                this.orm.searchCount("crm.lead", domain, { context: { active_test: false } })
            )
        );
        entries.forEach(([key], i) => {
            this.state[key] = results[i];
        });
        this.state.loading = false;
    }

    openLeads(key) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Leads / Opportunities",
            res_model: "crm.lead",
            views: [
                [false, "list"],
                [false, "form"],
                [false, "kanban"],
            ],
            domain: this.domains[key],
            context: { active_test: false },
        });
    }
}

registry.category("actions").add("exec_dashboard.crm_dashboard", CrmExecDashboard);
