/** @odoo-module **/
import {registry} from "@web/core/registry";
import {rpc} from "@web/core/network/rpc";
import {Component, onWillStart, onMounted, onWillUnmount, useState, useRef} from "@odoo/owl";

const COLORS = ["#6366f1", "#22d3ee", "#10b981", "#f59e0b", "#ef4444", "#a78bfa", "#ec4899", "#14b8a6", "#3b82f6", "#f97316"];

function getChart() {
    return window.Chart || (typeof Chart !== "undefined" ? Chart : null);
}

export class CRMDashboard extends Component {
    static template = "exec_dashboard.CRMDashboardTemplate";

    setup() {
        this.state = useState({
            total_leads: 0, open_leads: 0, new_leads: 0, in_progress: 0,
            won_leads: 0, lost_leads: 0, my_activities: 0, total_revenue: 0, new_stage_id: [],
            by_team_data: [], by_stage_data: [], by_source_data: [], loaded: false, error: null,
            filter_options: {teams: [], stages: [], sources: [], users: []},
            filters: {
                team_id: "", stage_id: "", source_id: "", user_id: "",
                priority: "", date_preset: "all", date_from: "", date_to: "",
            },
        });
        this.stageChartRef = useRef("stageChart");
        this.teamChartRef = useRef("teamChart");
        this.pipelineChartRef = useRef("pipelineChart");
        this.sourceChartRef = useRef("sourceChart");
        this._charts = [];
        this._mounted = false;

        onWillStart(async () => {
            await this.loadData();
        });
        onMounted(() => {
            this._mounted = true;
            this.scheduleRender();
        });
        onWillUnmount(() => {
            this._mounted = false;
            this.destroyCharts();
        });
    }

    async loadData() {
        try {
            const f = this.state.filters;
            const payload = {
                team_id: f.team_id || null,
                stage_id: f.stage_id || null,
                source_id: f.source_id || null,
                user_id: f.user_id || null,
                priority: f.priority || null,
                date_preset: f.date_preset || "all",
                date_from: f.date_from || null,
                date_to: f.date_to || null,
            };
            const data = await rpc("/exec_dashboard/get_crm_ultra_data", payload);
            if (data && data.error) {
                console.error("CRM Dashboard backend error:", data.error);
                this.state.error = data.error;
                this.state.loaded = true;
                return;
            }
            Object.assign(this.state, data);
            this.state.error = null;
            this.state.loaded = true;
            this.scheduleRender();
        } catch (e) {
            console.error("CRM Dashboard error:", e);
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
        Object.assign(this.state.filters, {
            team_id: "", stage_id: "", source_id: "", user_id: "",
            priority: "", date_preset: "all", date_from: "", date_to: "",
        });
        this.loadData();
    }

    get hasActiveFilters() {
        const f = this.state.filters;
        return !!(f.team_id || f.stage_id || f.source_id || f.user_id || f.priority || (f.date_preset && f.date_preset !== "all"));
    }

    scheduleRender() {
        if (!this._mounted || !this.state.loaded) return;
        // Wait for layout so canvas has size
        setTimeout(() => this.renderCharts(), 120);
    }

    destroyCharts() {
        (this._charts || []).forEach((c) => {
            try {
                c.destroy();
            } catch (_) {
            }
        });
        this._charts = [];
    }

    renderCharts() {
        const ChartLib = getChart();
        if (!ChartLib) {
            console.warn("Chart.js not available on window.Chart");
            return;
        }
        this.destroyCharts();

        // Pipeline Doughnut
        const pipeEl = this.pipelineChartRef.el;
        if (pipeEl) {
            const ch = new ChartLib(pipeEl, {
                type: "doughnut",
                data: {
                    labels: ["New", "In Progress", "Won", "Lost"],
                    datasets: [{
                        data: [
                            this.state.new_leads || 0,
                            this.state.in_progress || 0,
                            this.state.won_leads || 0,
                            this.state.lost_leads || 0,
                        ],
                        backgroundColor: ["#f59e0b", "#6366f1", "#10b981", "#ef4444"],
                        borderWidth: 0,
                        hoverOffset: 10,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "62%",
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {color: "#cbd5e1", padding: 14, font: {size: 11}},
                        },
                    },
                },
            });
            this._charts.push(ch);
        }

        // Stage Bar
        const stageEl = this.stageChartRef.el;
        if (stageEl) {
            const hasData = (this.state.by_stage_data || []).length > 0;
            const ch = new ChartLib(stageEl, {
                type: "bar",
                data: {
                    labels: hasData ? this.state.by_stage_data.map((i) => i.name) : ["No data"],
                    datasets: [{
                        label: "Leads",
                        data: hasData ? this.state.by_stage_data.map((i) => i.count) : [0],
                        backgroundColor: COLORS,
                        borderRadius: 8,
                        borderSkipped: false,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {legend: {display: false}},
                    scales: {
                        x: {ticks: {color: "#94a3b8", font: {size: 10}}, grid: {display: false}},
                        y: {ticks: {color: "#94a3b8"}, grid: {color: "rgba(148,163,184,0.12)"}, beginAtZero: true},
                    },
                },
            });
            this._charts.push(ch);
        }

        // Team Pie
        const teamEl = this.teamChartRef.el;
        if (teamEl) {
            const hasData = (this.state.by_team_data || []).length > 0;
            const ch = new ChartLib(teamEl, {
                type: "pie",
                data: {
                    labels: hasData ? this.state.by_team_data.map((i) => i.name) : ["No data"],
                    datasets: [{
                        data: hasData ? this.state.by_team_data.map((i) => i.count) : [1],
                        backgroundColor: hasData ? COLORS : ["#334155"],
                        borderWidth: 0,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "right",
                            labels: {color: "#cbd5e1", font: {size: 11}, boxWidth: 12},
                        },
                    },
                },
            });
            this._charts.push(ch);
        }

        // Source Bar (horizontal)
        const sourceEl = this.sourceChartRef.el;
        if (sourceEl) {
            const hasData = (this.state.by_source_data || []).length > 0;
            const ch = new ChartLib(sourceEl, {
                type: "bar",
                data: {
                    labels: hasData ? this.state.by_source_data.map((i) => i.name) : ["No data"],
                    datasets: [{
                        label: "Leads",
                        data: hasData ? this.state.by_source_data.map((i) => i.count) : [0],
                        backgroundColor: COLORS,
                        borderRadius: 6,
                        borderSkipped: false,
                    }],
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {legend: {display: false}},
                    scales: {
                        x: {ticks: {color: "#94a3b8"}, grid: {color: "rgba(148,163,184,0.12)"}, beginAtZero: true},
                        y: {ticks: {color: "#94a3b8", font: {size: 10}}, grid: {display: false}},
                    },
                },
            });
            this._charts.push(ch);
        }
    }

    openCRMAction(targetType) {
        // Every drilldown must stay scoped to Pipeline Opportunities only,
        // matching the KPI counts (which now exclude raw, not-yet-converted
        // Leads). Without this, clicking a card could open more records
        // than the number shown.
        let domain = [["type", "=", "opportunity"]];
        let name = "CRM Leads";
        if (targetType === "open") {
            domain.push(["active", "=", true], ["probability", "<", 100]);
            name = "Open Leads";
        } else if (targetType === "new") {
            // "New" = leads currently in the stage(s) literally named "New",
            // matching the KPI card count and the Pipeline kanban column
            // (not probability == 0, which can be 0 for later-stage leads too).
            if (this.state.new_stage_id && this.state.new_stage_id.length) {
                domain.push(["active", "=", true], ["stage_id", "in", this.state.new_stage_id]);
            } else {
                domain.push(["active", "=", true], ["probability", "=", 0]);
            }
            name = "New Leads";
        } else if (targetType === "in_progress") {
            if (this.state.new_stage_id && this.state.new_stage_id.length) {
                domain.push(["active", "=", true], ["probability", "<", 100], ["stage_id", "not in", this.state.new_stage_id]);
            } else {
                domain.push(["active", "=", true], ["probability", ">", 0], ["probability", "<", 100]);
            }
            name = "In Progress";
        } else if (targetType === "won") {
            domain.push(["active", "=", true], ["probability", "=", 100]);
            name = "Won Deals";
        } else if (targetType === "lost") {
            domain.push(["active", "=", false], ["probability", "=", 0]);
            name = "Lost Leads";
        } else if (targetType === "activities") {
            // Direct CRM Leads par filter laga kar activities open karne ka perfect tarika
            this.env.services.action.doAction({
                type: "ir.actions.act_window",
                name: "My Activities",
                res_model: "crm.lead",
                views: [[false, "list"], [false, "form"]],
                domain: [["activity_ids", "!=", false]],
                context: {
                    search_default_my_activities: 1,
                    search_default_activities_overdue: 1,
                    search_default_activities_today: 1,
                    search_default_activities_upcoming: 1
                },
                target: "current",
            });
            return;
        }
        // Respect active filters when drilling down
        const f = this.state.filters;
        if (f.team_id) domain.push(["team_id", "=", parseInt(f.team_id)]);
        if (f.stage_id) domain.push(["stage_id", "=", parseInt(f.stage_id)]);
        if (f.source_id) domain.push(["source_id", "=", parseInt(f.source_id)]);
        if (f.user_id) domain.push(["user_id", "=", parseInt(f.user_id)]);
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: "crm.lead",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }
}

registry
    .category(
        "actions"
    ).add(
    "crm_ultra_dashboard"
    ,
    CRMDashboard
)
;
