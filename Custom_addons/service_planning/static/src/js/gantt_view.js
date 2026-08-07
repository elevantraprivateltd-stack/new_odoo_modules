/** @odoo-module **/

import {Component, useState, onWillStart} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";


export class PlanningGanttRenderer extends Component {
    // Odoo Owl framework template assignment
    static template = "custom_planning_management.PlanningGanttTemplate";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            records: [],
            activeGridPeriods: [],
            scale: "week",
            referenceDate: new Date(),
            searchQuery: "",
            renderCounter: 0,
        });

        onWillStart(async () => {
            this.buildTimelineStructure();
            await this.loadRecords();
        });
    }

    async loadRecords() {
        const result = await this.orm.searchRead(
            "planning.schedule",
            [
                ["schedule_status", "!=", "deleted"],

            ],
            // employee_id ko employee_ids se replace kiya
            ["name", "employee_ids", "sale_order_id", "sale_order_line_id", "start_date", "end_date", "allocated_time_pct", "recurrency",
                "parent_schedule_id",]
        );
        this.state.records = result;
        this.state.renderCounter++;
    }

    buildTimelineStructure() {
        const ref = new Date(this.state.referenceDate);
        const periods = [];

        if (this.state.scale === "day") {
            for (let i = 0; i < 24; i += 2) {
                const startHour = new Date(ref);
                startHour.setHours(i, 0, 0, 0);
                const endHour = new Date(ref);
                endHour.setHours(i + 2, 0, 0, 0);

                periods.push({
                    id: `h-${i}`,
                    label: `${i === 0 ? '12' : i > 12 ? i - 12 : i} ${i >= 12 ? 'PM' : 'AM'}`,
                    sublabel: "Slot",
                    start: startHour,
                    end: endHour
                });
            }
        } else if (this.state.scale === "week") {
            const startOfWeek = new Date(ref);
            startOfWeek.setDate(ref.getDate() - ref.getDay());

            for (let i = 0; i < 7; i++) {
                const currentDay = new Date(startOfWeek);
                currentDay.setDate(startOfWeek.getDate() + i);

                periods.push({
                    id: `w-${i}`,
                    label: currentDay.toLocaleDateString('en-US', {weekday: 'long'}),
                    sublabel: currentDay.toLocaleDateString('en-US', {day: 'numeric', month: 'short'}),
                    start: new Date(currentDay.setHours(0, 0, 0, 0)),
                    end: new Date(currentDay.setHours(23, 59, 59, 999))
                });
            }
        } else if (this.state.scale === "month") {
            const year = ref.getFullYear();
            const month = ref.getMonth();
            const totalDays = new Date(year, month + 1, 0).getDate();

            for (let i = 1; i <= totalDays; i += 3) {
                const endDay = Math.min(i + 2, totalDays);
                periods.push({
                    id: `m-${i}`,
                    label: `Day ${i}-${endDay}`,
                    sublabel: ref.toLocaleDateString('en-US', {month: 'short'}),
                    start: new Date(year, month, i, 0, 0, 0),
                    end: new Date(year, month, endDay, 23, 59, 59)
                });
            }
        } else if (this.state.scale === "year") {
            const currentYear = ref.getFullYear();

            for (let i = 0; i < 12; i++) {

                const monthStart = new Date(currentYear, i, 1, 0, 0, 0);

                const monthEnd = new Date(
                    currentYear,
                    i + 1,
                    0,
                    23,
                    59,
                    59,
                    999
                );

                periods.push({
                    id: `y-${i}`,
                    label: monthStart.toLocaleDateString(
                        "en-US",
                        {month: "long"}
                    ),
                    sublabel: `${currentYear}`,
                    start: monthStart,
                    end: monthEnd,
                });
            }
        }
        this.state.activeGridPeriods = periods;
    }

    setTimeScale(newScale) {
        this.state.scale = newScale;
        this.buildTimelineStructure();
    }

    jumpToToday() {
        this.state.referenceDate = new Date();
        this.buildTimelineStructure();
    }

    navigateTime(direction) {
        const ref = new Date(this.state.referenceDate);
        if (this.state.scale === "day") ref.setDate(ref.getDate() + direction);
        if (this.state.scale === "week") ref.setDate(ref.getDate() + (direction * 7));
        if (this.state.scale === "month") ref.setMonth(ref.getMonth() + direction);
        if (this.state.scale === "year") ref.setFullYear(ref.getFullYear() + direction);

        this.state.referenceDate = ref;
        this.buildTimelineStructure();
    }

    clearSearch() {
        this.state.searchQuery = "";
    }

    // FIX: XML template k liye missing function yahan add kar diya ha
    getTotalVisibleRecords() {
        if (!this.state.records) return 0;
        return this.state.records.filter(rec => this.isRecordInActiveView(rec)).length;
    }

    formatActiveRangeLabel() {
        if (!this.state.activeGridPeriods.length) return "";
        const start = this.state.activeGridPeriods[0].start;
        const end = this.state.activeGridPeriods[this.state.activeGridPeriods.length - 1].end;

        return this.state.scale === 'day'
            ? start.toLocaleDateString('en-US', {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'})
            : `${start.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric'
            })} – ${end.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'})}`;
    }

    createNewAllocation() {
        this.openAllocationForm(false);
    }

    cellClickAdd(saleOrderId, startDateString) {
        const context = {
            'default_is_recurring': false,
            'default_recurrence_type': 'fortnightly'
        };

        if (saleOrderId) {
            context['default_sale_order_id'] = saleOrderId;
        }

        if (startDateString) {
            const clickedDate = new Date(startDateString);
            const year = clickedDate.getFullYear();
            const month = clickedDate.getMonth();
            const day = clickedDate.getDate();

            const offset = clickedDate.getTimezoneOffset() * 60000;

            const localStart = new Date(year, month, day, 9, 0, 0);
            const localEnd = new Date(year, month, day, 17, 0, 0);

            const utcStart = new Date(localStart.getTime() - offset);
            const utcEnd = new Date(localEnd.getTime() - offset);

            context['default_start_date'] = utcStart.toISOString().slice(0, 19).replace('T', ' ');
            context['default_end_date'] = utcEnd.toISOString().slice(0, 19).replace('T', ' ');
        }

        this.openAllocationForm(false, context);
    }

    openAllocationForm(resId = false, context = {}) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "planning.schedule",
            views: [[false, "form"]],
            res_id: resId,
            target: "new",
            context: context,
            // SERVICE PLANNING MODULE KA VIEW FORCE LOAD:
            view_id: "service_planning.view_planning_schedule_form_custom"
        }, {
            onClose: async () => {
                await this.loadRecords();
            }
        });
    }


    actionPublish() {
        alert("Allocations published successfully!");
    }

    isRecordInActiveView(rec) {
        if (!this.state.activeGridPeriods.length) return false;
        const viewStart = this.state.activeGridPeriods[0].start.getTime();
        const viewEnd = this.state.activeGridPeriods[this.state.activeGridPeriods.length - 1].end.getTime();
        const recStart = new Date(rec.start_date).getTime();
        const recEnd = new Date(rec.end_date).getTime();
        return recStart <= viewEnd && recEnd >= viewStart;
    }

    // Task 4: Helper formatting functions for Gantt bars duration display
    formatTimeRange(rec) {
        if (!rec.start_date || !rec.end_date) return "";
        const s = new Date(rec.start_date);
        const e = new Date(rec.end_date);
        return `${s.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric'
        })} - ${e.toLocaleDateString('en-US', {month: 'short', day: 'numeric'})}`;
    }


// Dynamic styling calculation for accurate positioning across different scales (Day, Week, Month, Year)
    getTaskStyle(rec) {

        if (
            !rec.start_date ||
            !rec.end_date ||
            !this.state.activeGridPeriods.length
        ) {
            return "display:none;";
        }

        const viewStart =
            this.state.activeGridPeriods[0].start.getTime();

        const viewEnd =
            this.state.activeGridPeriods[
            this.state.activeGridPeriods.length - 1
                ].end.getTime();

        const taskStart =
            new Date(rec.start_date).getTime();

        const taskEnd =
            new Date(rec.end_date).getTime();

        // Record view ke bahar ho to hide kar do
        if (
            taskEnd < viewStart ||
            taskStart > viewEnd
        ) {
            return "display:none;";
        }

        // calculate the visible area
        const visibleStart =
            Math.max(taskStart, viewStart);

        const visibleEnd =
            Math.min(taskEnd, viewEnd);

        const totalDuration =
            viewEnd - viewStart;

        const leftPercent =
            ((visibleStart - viewStart) /
                totalDuration) *
            100;

        const widthPercent =
            ((visibleEnd - visibleStart) /
                totalDuration) *
            100;

        return `
        left:${leftPercent}%;
        width:${Math.max(widthPercent, 1.5)}%;
        min-width:60px;
        z-index:10;
    `;
    }

    getOpenShifts() {
        return this.state.records.filter(
            rec =>
                !rec.sale_order_id &&
                rec.schedule_status !== "deleted" &&
                this.isRecordInActiveView(rec)
        );
    }

    getGroupedSaleOrders() {
        const groups = {};

        if (this.state && this.state.records) {
            this.state.records.forEach(rec => {

                // just skip the deleted record

                if (rec.sale_order_id) {
                    const soId = Array.isArray(rec.sale_order_id) ? rec.sale_order_id[0] : rec.sale_order_id;
                    const soName = Array.isArray(rec.sale_order_id) ? rec.sale_order_id[1] : rec.sale_order_id;

                    const assignmentName = rec.name || "";

                    if (!groups[soId]) {
                        groups[soId] = {
                            id: soId,
                            name: `${soName}\n${assignmentName}`,
                            shifts: [],
                        };
                    }

                    groups[soId].shifts.push(rec);
                }
            });
        }

        return Object.values(groups);
    }
}

registry
    .category(
        "actions"
    ).add(
    "planning_gantt_action"
    ,
    PlanningGanttRenderer
)
;


