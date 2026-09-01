/** @odoo-module **/
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";

const COLORS = ["#6366f1", "#22d3ee", "#10b981", "#f59e0b", "#ef4444", "#a78bfa", "#ec4899", "#14b8a6", "#3b82f6", "#f97316"];

function getChart() {
    return window.Chart || (typeof Chart !== "undefined" ? Chart : null);
}

export class ResourceDashboard extends Component {
    static template = "exec_dashboard.ResourceDashboardTemplate";

    setup() {
        this.state = useState({
            total_employees: 0, active_employees: 0, departments_count: 0,
            attendance_count: 0, leave_count: 0, available_count: 0,
            assigned_count: 0, dept_data: [], loaded: false,
            filter_options: { departments: [], jobs: [] },
            filters: { department_id: "", job_id: "" },
        });
        this.workforceChartRef = useRef("workforceChart");
        this.deptChartRef = useRef("deptChart");
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
                department_id: f.department_id || null,
                job_id: f.job_id || null,
            };
            const data = await rpc("/exec_dashboard/get_resource_ultra_data", payload);
            Object.assign(this.state, data);
            this.state.loaded = true;
            this.scheduleRender();
        } catch (e) {
            console.error("Resource Dashboard error:", e);
        }
    }

    onFilterChange(field, ev) {
        this.state.filters[field] = ev.target.value;
        this.loadData();
    }

    resetFilters() {
        Object.assign(this.state.filters, { department_id: "", job_id: "" });
        this.loadData();
    }

    get hasActiveFilters() {
        const f = this.state.filters;
        return !!(f.department_id || f.job_id);
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

        const wfEl = this.workforceChartRef.el;
        if (wfEl) {
            this._charts.push(new ChartLib(wfEl, {
                type: "doughnut",
                data: {
                    labels: ["Available", "On Leave", "Checked-In"],
                    datasets: [{
                        data: [
                            this.state.available_count || 0,
                            this.state.leave_count || 0,
                            this.state.attendance_count || 0,
                        ],
                        backgroundColor: ["#10b981", "#ef4444", "#22d3ee"],
                        borderWidth: 0, hoverOffset: 10,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false, cutout: "58%",
                    plugins: { legend: { position: "bottom", labels: { color: "#cbd5e1", padding: 12, font: { size: 11 } } } },
                },
            }));
        }

        const deptEl = this.deptChartRef.el;
        if (deptEl) {
            const hasData = (this.state.dept_data || []).length > 0;
            this._charts.push(new ChartLib(deptEl, {
                type: "bar",
                data: {
                    labels: hasData ? this.state.dept_data.map((i) => i.name) : ["No data"],
                    datasets: [{
                        label: "Employees",
                        data: hasData ? this.state.dept_data.map((i) => i.count) : [0],
                        backgroundColor: COLORS, borderRadius: 8, borderSkipped: false,
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

    openResourceAction(targetType) {
        let model = "hr.employee";
        let domain = [];
        let name = "Employees";
        if (targetType === "active") { domain = [["active", "=", true]]; name = "Active Employees"; }
        else if (targetType === "departments") { model = "hr.department"; name = "Departments"; }
        else if (targetType === "leaves") { model = "hr.leave"; domain = [["state", "=", "validate"]]; name = "Validated Leaves"; }
        const f = this.state.filters;
        if (model === "hr.employee") {
            if (f.department_id) domain.push(["department_id", "=", parseInt(f.department_id)]);
            if (f.job_id) domain.push(["job_id", "=", parseInt(f.job_id)]);
        }
        this.env.services.action.doAction({
            type: "ir.actions.act_window", name: name, res_model: model,
            views: [[false, "list"], [false, "kanban"], [false, "form"]], domain: domain, target: "current",
        });
    }
}

registry.category("actions").add("resource_ultra_dashboard", ResourceDashboard);
