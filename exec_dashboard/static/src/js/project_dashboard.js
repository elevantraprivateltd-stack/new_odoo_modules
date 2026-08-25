/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ProjectExecDashboard extends Component {
    static template = "exec_dashboard.ProjectDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            activeProjects: 0,
            openTasks: 0,
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    get domains() {
        return {
            activeProjects: [["active", "=", true]],
            openTasks: [["state", "not in", ["1_done", "1_canceled"]]],
        };
    }

    async loadData() {
        this.state.loading = true;
        const [activeProjects, openTasks] = await Promise.all([
            this.orm.searchCount("project.project", this.domains.activeProjects),
            this.orm.searchCount("project.task", this.domains.openTasks),
        ]);
        this.state.activeProjects = activeProjects;
        this.state.openTasks = openTasks;
        this.state.loading = false;
    }

    openProjects() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Projects",
            res_model: "project.project",
            views: [
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
            ],
            domain: this.domains.activeProjects,
        });
    }

    openTasks() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Tasks",
            res_model: "project.task",
            views: [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
            ],
            domain: this.domains.openTasks,
        });
    }
}

registry.category("actions").add("exec_dashboard.project_dashboard", ProjectExecDashboard);
