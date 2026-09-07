/** @odoo-module **/
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";

const COLORS = ["#6366f1", "#22d3ee", "#10b981", "#f59e0b", "#ef4444", "#a78bfa", "#ec4899", "#14b8a6", "#3b82f6", "#f97316"];

function getChart() {
    return window.Chart || (typeof Chart !== "undefined" ? Chart : null);
}

export class SaleDashboard extends Component {
    static template = "exec_dashboard.SaleDashboardTemplate";

    setup() {
        this.state = useState({
            total_orders: 0, quotations: 0, sale_confirmed: 0, cancelled: 0,
            to_invoice: 0, upsell: 0, fully_invoiced: 0, customers_count: 0,
            total_sales: 0, salesperson_data: [], loaded: false, error: null,
            filter_options: { teams: [], users: [], states: [] },
            filters: { team_id: "", user_id: "", state: "", date_preset: "all", date_from: "", date_to: "" },
        });
        this.statusChartRef = useRef("statusChart");
        this.spChartRef = useRef("spChart");
        this.invoiceChartRef = useRef("invoiceChart");
        this._charts = [];
        this._mounted = false;

        onWillStart(async () => { await this.loadData(); });
        onMounted(() => { this._mounted = true; this.scheduleRender(); });
        onWillUnmount(() => { this._mounted = false; this.destroyCharts(); });
    }

    async loadData() {
        try {
            const f = this.state.filters;
            const payload = {
                team_id: f.team_id || null,
                user_id: f.user_id || null,
                state: f.state || null,
                date_preset: f.date_preset || "all",
                date_from: f.date_from || null,
                date_to: f.date_to || null,
            };
            const data = await rpc("/exec_dashboard/get_sale_ultra_data", payload);
            if (data && data.error) {
                console.error("Sale Dashboard backend error:", data.error);
                this.state.error = data.error;
                this.state.loaded = true;
                return;
            }
Object.assign(this.state, data);
            this.state.error = null;
            this.state.loaded = true;
            this.scheduleRender();
        } catch (e) {
            console.error("Sale Dashboard error:", e);
            this.state.error = (e && e.message) ? e.message : String(e);
            this.state.loaded = true;
        }
    }

    onFilterChange(field, ev) {
        this.state.filters[field] = ev.target.value;
        if (field === "date_preset" && ev.target.value !== "custom") {
            this.state.filters.date_from = "";
            this.state.filters.date_to = "";
        }
        this.loadData();
    }

    resetFilters() {
        Object.assign(this.state.filters, { team_id: "", user_id: "", state: "", date_preset: "all", date_from: "", date_to: "" });
        this.loadData();
    }

    get hasActiveFilters() {
        const f = this.state.filters;
        return !!(f.team_id || f.user_id || f.state || (f.date_preset && f.date_preset !== "all"));
    }

    scheduleRender() {
        if (!this._mounted || !this.state.loaded) return;
        setTimeout(() => this.renderCharts(), 120);
    }

    destroyCharts() {
        (this._charts || []).forEach((c) => { try { c.destroy(); } catch (_) {} });
        this._charts = [];
    }

    renderCharts() {
        const ChartLib = getChart();
        if (!ChartLib) return;
        this.destroyCharts();

        const statusEl = this.statusChartRef.el;
        if (statusEl) {
            this._charts.push(new ChartLib(statusEl, {
                type: "doughnut",
                data: {
                    labels: ["Quotations", "Confirmed", "Cancelled"],
                    datasets: [{
                        data: [this.state.quotations || 0, this.state.sale_confirmed || 0, this.state.cancelled || 0],
                        backgroundColor: ["#f59e0b", "#10b981", "#ef4444"],
                        borderWidth: 0, hoverOffset: 10,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false, cutout: "60%",
                    plugins: { legend: { position: "bottom", labels: { color: "#cbd5e1", padding: 12, font: { size: 11 } } } },
                },
            }));
        }

        const invEl = this.invoiceChartRef.el;
        if (invEl) {
            this._charts.push(new ChartLib(invEl, {
                type: "bar",
                data: {
                    labels: ["To Invoice", "Upselling", "Fully Invoiced"],
                    datasets: [{
                        label: "Orders",
                        data: [this.state.to_invoice || 0, this.state.upsell || 0, this.state.fully_invoiced || 0],
                        backgroundColor: ["#6366f1", "#a78bfa", "#10b981"],
                        borderRadius: 10, borderSkipped: false,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: "#94a3b8" }, grid: { display: false } },
                        y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.12)" }, beginAtZero: true },
                    },
                },
            }));
        }

        const spEl = this.spChartRef.el;
        if (spEl) {
            const hasData = (this.state.salesperson_data || []).length > 0;
            this._charts.push(new ChartLib(spEl, {
                type: "bar",
                data: {
                    labels: hasData ? this.state.salesperson_data.map((i) => i.name) : ["No data"],
                    datasets: [{
                        label: "Confirmed Orders",
                        data: hasData ? this.state.salesperson_data.map((i) => i.count) : [0],
                        backgroundColor: COLORS, borderRadius: 6, borderSkipped: false,
                    }],
                },
                options: {
                    indexAxis: "y",
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.12)" }, beginAtZero: true },
                        y: { ticks: { color: "#94a3b8", font: { size: 10 } }, grid: { display: false } },
                    },
                },
            }));
        }
    }

    openSalesAction(targetType) {
        let domain = [];
        let name = "Sales Orders";
        if (targetType === "quotation") { domain = [["state", "in", ["draft", "sent"]]]; name = "Quotations"; }
        else if (targetType === "confirmed") { domain = [["state", "=", "sale"]]; name = "Confirmed Sales"; }
        else if (targetType === "cancel") { domain = [["state", "=", "cancel"]]; name = "Cancelled"; }
        else if (targetType === "to_invoice") { domain = [["invoice_status", "=", "to invoice"]]; name = "To Invoice"; }
        else if (targetType === "upsell") { domain = [["invoice_status", "=", "upselling"]]; name = "Upselling"; }
        else if (targetType === "invoiced") { domain = [["invoice_status", "=", "invoiced"]]; name = "Fully Invoiced"; }
        else if (targetType === "customers") {
            this.env.services.action.doAction({
                type: "ir.actions.act_window", name: "Customers", res_model: "res.partner",
                views: [[false, "list"], [false, "form"]], domain: [["customer_rank", ">", 0]], target: "current",
            });
            return;
        }
        const f = this.state.filters;
        if (f.team_id) domain.push(["team_id", "=", parseInt(f.team_id)]);
        if (f.user_id) domain.push(["user_id", "=", parseInt(f.user_id)]);
        this.env.services.action.doAction({
            type: "ir.actions.act_window", name: name, res_model: "sale.order",
            views: [[false, "list"], [false, "form"], [false, "kanban"]], domain: domain, target: "current",
        });
    }
}

registry.category("actions").add("sale_ultra_dashboard", SaleDashboard);
