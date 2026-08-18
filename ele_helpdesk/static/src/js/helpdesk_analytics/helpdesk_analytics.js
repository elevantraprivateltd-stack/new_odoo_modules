/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

// Fixed color palette re-used for both the pie chart (by stage) and the
// stacked bar chart (by team) so colors stay consistent across the page.
const PALETTE = [
    "#4c9aff", "#e5739d", "#2f9e6e", "#e0883b",
    "#9b7dde", "#3fb6c9", "#c96f6f", "#7c9c3f",
];

export class HelpdeskAnalyticsDashboard extends Component {
    static template = "ele_helpdesk.HelpdeskAnalyticsDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            data: null,
            customers: [],
            partnerId: false,
            loading: true,
        });

        onWillStart(async () => {
            await this.loadCustomers();
            await this.loadData();
        });
    }

    async loadCustomers() {
        this.state.customers = await this.orm.call(
            "helpdesk.ticket",
            "get_dashboard_customers",
            []
        );
    }

    async loadData() {
        this.state.loading = true;
        const data = await this.orm.call(
            "helpdesk.ticket",
            "get_analytics_dashboard_data",
            [this.state.partnerId || false]
        );
        this.state.data = data;
        this.state.loading = false;
    }

    onCustomerChange(ev) {
        const val = ev.target.value;
        this.state.partnerId = val ? parseInt(val, 10) : false;
        this.loadData();
    }

    onRefreshClick() {
        this.loadData();
    }

    color(index) {
        return PALETTE[index % PALETTE.length];
    }

    // ---------------------------------------------------------------
    // Pie chart: tickets grouped by stage. Returns an array of wedge
    // descriptors ready to be drawn as SVG <path> "d" attributes.
    // ---------------------------------------------------------------
    get pieSlices() {
        const rows = (this.state.data && this.state.data.stage_breakdown) || [];
        const total = rows.reduce((sum, r) => sum + r.count, 0);
        if (!total) {
            return [];
        }
        const cx = 110, cy = 110, r = 100;
        let angle = -Math.PI / 2; // start at 12 o'clock
        const slices = [];
        rows.forEach((row, index) => {
            const fraction = row.count / total;
            const sweep = fraction * Math.PI * 2;
            const x1 = cx + r * Math.cos(angle);
            const y1 = cy + r * Math.sin(angle);
            const endAngle = angle + sweep;
            const x2 = cx + r * Math.cos(endAngle);
            const y2 = cy + r * Math.sin(endAngle);
            const largeArc = sweep > Math.PI ? 1 : 0;
            let d;
            if (rows.length === 1) {
                // A single 100% slice can't be drawn as an arc path -> full circle.
                d = `M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy} A ${r} ${r} 0 1 1 ${cx - r} ${cy} Z`;
            } else {
                d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
            }
            slices.push({
                d,
                color: this.color(index),
                name: row.name,
                count: row.count,
                pct: Math.round(fraction * 1000) / 10,
            });
            angle = endAngle;
        });
        return slices;
    }

    // ---------------------------------------------------------------
    // Stacked bar chart: X axis = stage, stacked segments = team.
    // ---------------------------------------------------------------
    get barChart() {
        const data = this.state.data;
        if (!data) {
            return { stages: [], teams: [], maxTotal: 0 };
        }
        const stages = data.stages || [];
        const teams = data.team_stage_breakdown || [];
        const totals = stages.map((stage) =>
            teams.reduce((sum, team) => sum + (team.stages[String(stage.id)] || 0), 0)
        );
        const maxTotal = Math.max(1, ...totals);
        const bars = stages.map((stage, sIndex) => {
            let cumulative = 0;
            const segments = teams.map((team, tIndex) => {
                const value = team.stages[String(stage.id)] || 0;
                const segment = {
                    value,
                    color: this.color(tIndex),
                    teamName: team.name,
                    heightPct: (value / maxTotal) * 100,
                    bottomPct: (cumulative / maxTotal) * 100,
                };
                cumulative += value;
                return segment;
            }).filter((seg) => seg.value > 0);
            return { name: stage.name, total: totals[sIndex], segments };
        });
        return { bars, teams, maxTotal };
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
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }
}

registry.category("actions").add("helpdesk_analytics_dashboard", HelpdeskAnalyticsDashboard);
