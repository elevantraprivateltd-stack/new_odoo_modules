/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

const REFRESH_INTERVAL_MS = 20000; // auto-refresh every 20s -> "live" dashboard

export class HelpdeskDashboard extends Component {
    static template = "ele_helpdesk.HelpdeskDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.uid = user.userId;

        this.state = useState({
            data: null,
            customers: [],
            partnerId: false,
            loading: true,
            lastUpdated: null,
        });

        onWillStart(async () => {
            await this.loadCustomers();
            await this.loadData();
        });

        onMounted(() => {
            this.timer = setInterval(() => this.loadData(true), REFRESH_INTERVAL_MS);
        });

        onWillUnmount(() => {
            clearInterval(this.timer);
        });
    }

    async loadCustomers() {
        this.state.customers = await this.orm.call(
            "helpdesk.ticket",
            "get_dashboard_customers",
            []
        );
    }

    async loadData(silent = false) {
        if (!silent) {
            this.state.loading = true;
        }
        const data = await this.orm.call(
            "helpdesk.ticket",
            "get_dashboard_data",
            [this.state.partnerId || false]
        );
        this.state.data = data;
        this.state.loading = false;
        this.state.lastUpdated = new Date();
    }

    onCustomerChange(ev) {
        const val = ev.target.value;
        this.state.partnerId = val ? parseInt(val, 10) : false;
        this.loadData();
    }

    onRefreshClick() {
        this.loadData();
    }

    openTickets(extraDomain) {
        const domain = extraDomain ? [...extraDomain] : [];
        if (this.state.partnerId) {
            domain.push(["partner_id", "=", this.state.partnerId]);
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Tickets",
            res_model: "helpdesk.ticket",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain,
        });
    }

    openTeamTickets(team, extraDomain) {
        const domain = [["team_id", "=", team.id], ...(extraDomain || [])];
        this.openTickets(domain);
    }
}

registry.category("actions").add("helpdesk_dashboard", HelpdeskDashboard);
