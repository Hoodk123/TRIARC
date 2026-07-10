"""TRIARC TUI (architecture.md #8; roadmap Phase 4): a terminal dashboard over the
management API -- the same four views as the web client (ui/web/), reachable through
the same API calls. Run with: `python -m ui.tui.app` from the repo root (needs
`pip install -e .[tui]`).
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static, TabbedContent, TabPane

from ui.tui.api_client import ApiClient

_LIST_POLL_SECONDS = 2.0
_DETAIL_POLL_SECONDS = 1.0

_RUN_STATUS_LABEL = {
    "pending": "PENDING",
    "running": "RUNNING",
    "completed": "COMPLETED",
    "failed": "FAILED",
    "cancelled": "CANCELLED",
}
_TERMINAL_RUN_STATUSES = {"completed", "failed", "cancelled"}


class RunsView(Vertical):
    """Run monitoring & control, plus cost & routing telemetry for the selected run."""

    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self._api = api
        self._selected_run_id: str | None = None

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Input(placeholder="add JWT auth to this Flask app and write tests", id="goal-input"),
            Button("Start run", id="start-run-btn", variant="primary"),
            id="start-run-row",
        )
        yield DataTable(id="runs-table", cursor_type="row")
        yield Static("Select a run to see its steps and telemetry.", id="run-detail-label")
        yield Button("Cancel selected run", id="cancel-run-btn")
        yield DataTable(id="steps-table", cursor_type="row")
        yield DataTable(id="telemetry-table", cursor_type="row")
        yield Static("", id="cost-summary")

    def on_mount(self) -> None:
        runs_table = self.query_one("#runs-table", DataTable)
        runs_table.add_columns("Status", "Goal")

        steps_table = self.query_one("#steps-table", DataTable)
        steps_table.add_columns("Step", "Endpoint", "Attempts", "Passed", "Escalations")

        telemetry_table = self.query_one("#telemetry-table", DataTable)
        telemetry_table.add_columns(
            "Task", "Tier", "Endpoint", "Tokens", "Cost", "Confidence", "Escalated", "Passed"
        )

        self.set_interval(_LIST_POLL_SECONDS, self.refresh_runs)
        self.set_interval(_DETAIL_POLL_SECONDS, self.refresh_selected_run)
        self.run_worker(self.refresh_runs())

    async def refresh_runs(self) -> None:
        runs = await self._api.list_runs()
        table = self.query_one("#runs-table", DataTable)
        table.clear()
        for run in runs:
            table.add_row(_RUN_STATUS_LABEL.get(run["status"], run["status"]), run["goal"], key=run["run_id"])

    async def refresh_selected_run(self) -> None:
        if self._selected_run_id is None:
            return
        await self._show_run(self._selected_run_id)

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "runs-table":
            return
        self._selected_run_id = str(event.row_key.value)
        await self._show_run(self._selected_run_id)

    async def _show_run(self, run_id: str) -> None:
        run = await self._api.get_run(run_id)

        label = self.query_one("#run-detail-label", Static)
        label.update(f"{run['goal']}  [{_RUN_STATUS_LABEL.get(run['status'], run['status'])}]")

        steps_table = self.query_one("#steps-table", DataTable)
        steps_table.clear()
        outcomes_by_task = {outcome["task_id"]: outcome for outcome in run["outcomes"]}
        for step in run["routed_steps"]:
            outcome = outcomes_by_task.get(step["task"]["task_id"])
            steps_table.add_row(
                step["task"]["goal"],
                step["endpoint_id"],
                str(outcome["attempts"]) if outcome else "-",
                ("yes" if outcome["passed"] else "no") if outcome else "-",
                "; ".join(outcome["escalations"]) if outcome else "-",
            )

        telemetry_table = self.query_one("#telemetry-table", DataTable)
        telemetry_table.clear()
        for log in run["telemetry"]:
            telemetry_table.add_row(
                log["goal"],
                str(log["tier"]) if log["tier"] is not None else "-",
                log["endpoint_id"],
                str(log["tokens"]),
                f"{log['cost']:.2f}",
                f"{log['confidence']:.2f}",
                "yes" if log["escalated"] else "no",
                "-" if log["passed"] is None else ("yes" if log["passed"] else "no"),
            )

        summary = self.query_one("#cost-summary", Static)
        if run["cost_summary"]:
            cost = run["cost_summary"]
            summary.update(
                f"Steps: {cost['step_count']}  Escalated: {cost['escalated_count']}  "
                f"Actual: {cost['actual_cost']:.2f}  Baseline: {cost['baseline_cost']:.2f}  "
                f"Savings: {cost['savings']:.2f}"
            )
        else:
            summary.update("")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-run-btn":
            goal_input = self.query_one("#goal-input", Input)
            goal = goal_input.value.strip()
            if not goal:
                return
            await self._api.start_run(goal)
            goal_input.value = ""
            await self.refresh_runs()
        elif event.button.id == "cancel-run-btn":
            if self._selected_run_id is not None:
                await self._api.cancel_run(self._selected_run_id)
                await self._show_run(self._selected_run_id)


class RegistryView(Vertical):
    """Model registry editor: view/edit configs/models.yaml entries."""

    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self._api = api
        self._selected_model_id: str | None = None

    def compose(self) -> ComposeResult:
        yield DataTable(id="registry-table", cursor_type="row")
        yield Horizontal(
            Input(placeholder="new cost", id="cost-input"),
            Button("Update cost", id="update-cost-btn", variant="primary"),
        )

    def on_mount(self) -> None:
        table = self.query_one("#registry-table", DataTable)
        table.add_columns("ID", "Tier", "Endpoint", "Capabilities", "Cost", "Privacy")
        self.run_worker(self.refresh_registry())

    async def refresh_registry(self) -> None:
        entries = await self._api.get_registry()
        table = self.query_one("#registry-table", DataTable)
        table.clear()
        for entry in entries:
            table.add_row(
                entry["id"],
                str(entry["tier"]) if entry["tier"] is not None else "-",
                entry["endpoint"],
                ", ".join(entry["capabilities"]),
                f"{entry['cost']:.2f}",
                entry["privacy"],
                key=entry["id"],
            )

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._selected_model_id = str(event.row_key.value)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "update-cost-btn" or self._selected_model_id is None:
            return
        cost_input = self.query_one("#cost-input", Input)
        try:
            cost = float(cost_input.value)
        except ValueError:
            return
        await self._api.update_registry_entry(self._selected_model_id, cost=cost)
        cost_input.value = ""
        await self.refresh_registry()


class GatesView(Vertical):
    """Confirmation gate inbox: approve/deny pending gates."""

    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self._api = api
        self._selected_gate_id: str | None = None

    def compose(self) -> ComposeResult:
        yield DataTable(id="gates-table", cursor_type="row")
        yield Horizontal(
            Button("Approve", id="approve-btn", variant="success"),
            Button("Deny", id="deny-btn", variant="error"),
        )
        yield Static("Egress redaction log", id="redaction-log-label")
        yield DataTable(id="redaction-log-table")

    def on_mount(self) -> None:
        table = self.query_one("#gates-table", DataTable)
        table.add_columns("Action", "Detail", "Decision")

        redaction_table = self.query_one("#redaction-log-table", DataTable)
        redaction_table.add_columns("Timestamp", "Kind", "Matched")

        self.set_interval(_LIST_POLL_SECONDS, self.refresh_gates)
        self.set_interval(_LIST_POLL_SECONDS, self.refresh_redaction_log)
        self.run_worker(self.refresh_gates())
        self.run_worker(self.refresh_redaction_log())

    async def refresh_gates(self) -> None:
        gates = await self._api.list_gates()
        table = self.query_one("#gates-table", DataTable)
        table.clear()
        for gate in gates:
            table.add_row(gate["action"], gate["detail"], gate["decision"], key=gate["gate_id"])

    async def refresh_redaction_log(self) -> None:
        entries = await self._api.get_redaction_log()
        table = self.query_one("#redaction-log-table", DataTable)
        table.clear()
        for entry in entries:
            table.add_row(entry["timestamp"], entry["kind"], entry["matched"])

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._selected_gate_id = str(event.row_key.value)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self._selected_gate_id is None:
            return
        if event.button.id == "approve-btn":
            await self._api.resolve_gate(self._selected_gate_id, approved=True)
        elif event.button.id == "deny-btn":
            await self._api.resolve_gate(self._selected_gate_id, approved=False)
        else:
            return
        await self.refresh_gates()


class TriarcTUI(App):
    """TRIARC management dashboard."""

    CSS_PATH = "app.css"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, api: ApiClient | None = None) -> None:
        super().__init__()
        self._api = api or ApiClient()

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Runs", id="tab-runs"):
                yield RunsView(self._api)
            with TabPane("Model registry", id="tab-registry"):
                yield RegistryView(self._api)
            with TabPane("Confirmation gates", id="tab-gates"):
                yield GatesView(self._api)
        yield Footer()

    async def on_unmount(self) -> None:
        await self._api.close()


if __name__ == "__main__":
    TriarcTUI().run()
