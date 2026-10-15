/** @odoo-module **/
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";

const COLORS = ["#6366f1", "#22d3ee", "#10b981", "#f59e0b", "#ef4444", "#a78bfa", "#ec4899", "#14b8a6", "#3b82f6", "#f97316"];

function getChart() {
    return window.Chart || (typeof Chart !== "undefined" ? Chart : null);
}

export class ProjectDashboard extends Component {
    static template = "ele_exective_summary.ProjectDashboardTemplate";

    setup() {
        this.state = useState({
            total_projects: 0, open_projects: 0, total_tasks: 0,
            open_tasks: 0, done_tasks: 0, my_tasks: 0, tags_count: 0,
            stage_data: [], loaded: false, error: null,
            filter_options: { projects: [], stages: [], users: [] },
            filters: { project_id: "", stage_id: "", user_id: "", date_preset: "all", date_from: "", date_to: "" },
        });
        this.taskChartRef = useRef("taskChart");
        this.stageChartRef = useRef("stageChart");
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
                project_id: f.project_id || null,
                stage_id: f.stage_id || null,
                user_id: f.user_id || null,
                date_preset: f.date_preset || "all",
                date_from: f.date_from || null,
                date_to: f.date_to || null,
            };
            const data = await rpc("/ele_exective_summary/get_project_ultra_data", payload);
            if (data && data.error) {
                console.error("Project Dashboard backend error:", data.error);
                this.state.error = data.error;
                this.state.loaded = true;
                return;
            }
Object.assign(this.state, data);
            this.state.error = null;
            this.state.loaded = true;
            this.scheduleRender();
        } catch (e) {
            console.error("Project Dashboard error:", e);
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
        Object.assign(this.state.filters, { project_id: "", stage_id: "", user_id: "", date_preset: "all", date_from: "", date_to: "" });
        this.loadData();
    }

    get hasActiveFilters() {
        const f = this.state.filters;
        return !!(f.project_id || f.stage_id || f.user_id || (f.date_preset && f.date_preset !== "all"));
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

        const taskEl = this.taskChartRef.el;
        if (taskEl) {
            this._charts.push(new ChartLib(taskEl, {
                type: "doughnut",
                data: {
                    labels: ["Open Tasks", "Done Tasks", "My Tasks"],
                    datasets: [{
                        data: [this.state.open_tasks || 0, this.state.done_tasks || 0, this.state.my_tasks || 0],
                        backgroundColor: ["#6366f1", "#10b981", "#22d3ee"],
                        borderWidth: 0, hoverOffset: 10,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false, cutout: "58%",
                    plugins: { legend: { position: "bottom", labels: { color: "#cbd5e1", padding: 12, font: { size: 11 } } } },
                },
            }));
        }

        const stageEl = this.stageChartRef.el;
        if (stageEl) {
            const hasData = (this.state.stage_data || []).length > 0;
            this._charts.push(new ChartLib(stageEl, {
                type: "bar",
                data: {
                    labels: hasData ? this.state.stage_data.map((i) => i.name) : ["No data"],
                    datasets: [{
                        label: "Tasks",
                        data: hasData ? this.state.stage_data.map((i) => i.count) : [0],
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

    openProjectAction(targetType) {
        let model = "project.task";
        let domain = [];
        let name = "Tasks";
        if (targetType === "projects") { model = "project.project"; name = "Projects"; }
        else if (targetType === "open_projects") { model = "project.project"; domain = [["active", "=", true]]; name = "Open Projects"; }
        else if (targetType === "my_tasks") { domain = [["user_ids", "in", [user.userId]]]; name = "My Tasks"; }
        else if (targetType === "open_tasks") { domain = [["stage_id.fold", "=", false]]; name = "Open Tasks"; }
        else if (targetType === "done_tasks") { domain = [["stage_id.fold", "=", true]]; name = "Done Tasks"; }
        const f = this.state.filters;
        if (model === "project.task") {
            if (f.project_id) domain.push(["project_id", "=", parseInt(f.project_id)]);
            if (f.stage_id) domain.push(["stage_id", "=", parseInt(f.stage_id)]);
            if (f.user_id) domain.push(["user_ids", "in", [parseInt(f.user_id)]]);
        }
        this.env.services.action.doAction({
            type: "ir.actions.act_window", name: name, res_model: model,
            views: [[false, "list"], [false, "kanban"], [false, "form"]], domain: domain, target: "current",
        });
    }
}

registry.category("actions").add("project_ultra_dashboard", ProjectDashboard);
