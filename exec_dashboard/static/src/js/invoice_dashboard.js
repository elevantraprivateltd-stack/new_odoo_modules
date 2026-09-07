/** @odoo-module **/
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";

function getChart() {
    return window.Chart || (typeof Chart !== "undefined" ? Chart : null);
}

export class InvoiceDashboard extends Component {
    static template = "exec_dashboard.InvoiceDashboardTemplate";

    setup() {
        this.state = useState({
            total_invoices: 0, draft_invoices: 0, posted_invoices: 0,
            unpaid_invoices: 0, paid_invoices: 0, bills_count: 0,
            refunds_count: 0, vendors_count: 0,
            total_sale_amount: 0, total_purchase_amount: 0,
            payments_collected: 0, residual_amount: 0, loaded: false, error: null,
            filter_options: { partners: [], users: [], payment_states: [] },
            filters: { partner_id: "", user_id: "", payment_state: "", date_preset: "all", date_from: "", date_to: "" },
        });
        this.statusChartRef = useRef("statusChart");
        this.paymentChartRef = useRef("paymentChart");
        this.amountChartRef = useRef("amountChart");
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
                partner_id: f.partner_id || null,
                user_id: f.user_id || null,
                payment_state: f.payment_state || null,
                date_preset: f.date_preset || "all",
                date_from: f.date_from || null,
                date_to: f.date_to || null,
            };
            const data = await rpc("/exec_dashboard/get_invoice_ultra_data", payload);
            if (data && data.error) {
                console.error("Invoice Dashboard backend error:", data.error);
                this.state.error = data.error;
                this.state.loaded = true;
                return;
            }
Object.assign(this.state, data);
            this.state.error = null;
            this.state.loaded = true;
            this.scheduleRender();
        } catch (e) {
            console.error("Invoice Dashboard error:", e);
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
        Object.assign(this.state.filters, { partner_id: "", user_id: "", payment_state: "", date_preset: "all", date_from: "", date_to: "" });
        this.loadData();
    }

    get hasActiveFilters() {
        const f = this.state.filters;
        return !!(f.partner_id || f.user_id || f.payment_state || (f.date_preset && f.date_preset !== "all"));
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
                    labels: ["Draft", "Posted", "Unpaid", "Paid"],
                    datasets: [{
                        data: [
                            this.state.draft_invoices || 0,
                            this.state.posted_invoices || 0,
                            this.state.unpaid_invoices || 0,
                            this.state.paid_invoices || 0,
                        ],
                        backgroundColor: ["#94a3b8", "#6366f1", "#ef4444", "#10b981"],
                        borderWidth: 0, hoverOffset: 10,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false, cutout: "60%",
                    plugins: { legend: { position: "bottom", labels: { color: "#cbd5e1", padding: 12, font: { size: 11 } } } },
                },
            }));
        }

        const payEl = this.paymentChartRef.el;
        if (payEl) {
            this._charts.push(new ChartLib(payEl, {
                type: "pie",
                data: {
                    labels: ["Collected", "Outstanding"],
                    datasets: [{
                        data: [this.state.payments_collected || 0, this.state.residual_amount || 0],
                        backgroundColor: ["#10b981", "#f59e0b"],
                        borderWidth: 0,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: "bottom", labels: { color: "#cbd5e1", padding: 12, font: { size: 11 } } } },
                },
            }));
        }

        const amtEl = this.amountChartRef.el;
        if (amtEl) {
            this._charts.push(new ChartLib(amtEl, {
                type: "bar",
                data: {
                    labels: ["Sales Amount", "Purchase Amount", "Collected", "Residual"],
                    datasets: [{
                        label: "Amount",
                        data: [
                            this.state.total_sale_amount || 0,
                            this.state.total_purchase_amount || 0,
                            this.state.payments_collected || 0,
                            this.state.residual_amount || 0,
                        ],
                        backgroundColor: ["#10b981", "#ef4444", "#22d3ee", "#f59e0b"],
                        borderRadius: 10, borderSkipped: false,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: "#94a3b8", font: { size: 10 } }, grid: { display: false } },
                        y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.12)" }, beginAtZero: true },
                    },
                },
            }));
        }
    }

    openInvoiceAction(targetType) {
        let domain = [];
        let model = "account.move";
        let name = "Invoices";
        if (targetType === "customer_invoice") { domain = [["move_type", "=", "out_invoice"]]; name = "Customer Invoices"; }
        else if (targetType === "draft") { domain = [["move_type", "=", "out_invoice"], ["state", "=", "draft"]]; name = "Draft Invoices"; }
        else if (targetType === "posted") { domain = [["move_type", "=", "out_invoice"], ["state", "=", "posted"]]; name = "Posted Invoices"; }
        else if (targetType === "unpaid") {
            domain = [["move_type", "=", "out_invoice"], ["state", "=", "posted"], ["payment_state", "in", ["not_paid", "partial"]]];
            name = "Unpaid Invoices";
        } else if (targetType === "paid") {
            domain = [["move_type", "=", "out_invoice"], ["state", "=", "posted"], ["payment_state", "=", "paid"]];
            name = "Paid Invoices";
        } else if (targetType === "vendor_bill") { domain = [["move_type", "=", "in_invoice"]]; name = "Vendor Bills"; }
        else if (targetType === "refund") { domain = [["move_type", "=", "out_refund"]]; name = "Credit Notes"; }
        else if (targetType === "vendor") {
            model = "res.partner"; domain = [["supplier_rank", ">", 0]]; name = "Vendors";
        }
        const f = this.state.filters;
        if (model === "account.move") {
            if (f.partner_id) domain.push(["partner_id", "=", parseInt(f.partner_id)]);
            if (f.user_id) domain.push(["invoice_user_id", "=", parseInt(f.user_id)]);
        }
        this.env.services.action.doAction({
            type: "ir.actions.act_window", name: name, res_model: model,
            views: [[false, "list"], [false, "form"]], domain: domain, target: "current",
        });
    }
}

registry.category("actions").add("invoice_ultra_dashboard", InvoiceDashboard);
