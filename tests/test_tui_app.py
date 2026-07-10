from textual.widgets import Button, DataTable
from textual.widgets.data_table import RowKey

from ui.tui.app import GatesView, RegistryView, RunsView, TriarcTUI


class _FakeApiClient:
    def __init__(self) -> None:
        self.run_summaries = [{"run_id": "r1", "goal": "add JWT auth", "status": "completed"}]
        self.run_detail = {
            "run_id": "r1",
            "goal": "add JWT auth",
            "status": "completed",
            "routed_steps": [
                {"endpoint_id": "gemma-coder", "task": {"task_id": "t1", "goal": "scaffold routes"}}
            ],
            "outcomes": [{"task_id": "t1", "attempts": 1, "passed": True, "escalations": []}],
            "telemetry": [
                {
                    "task_id": "t1",
                    "goal": "scaffold routes",
                    "tier": 2,
                    "endpoint_id": "gemma-coder",
                    "tokens": 100,
                    "cost": 0.2,
                    "confidence": 0.9,
                    "escalated": False,
                    "passed": True,
                }
            ],
            "cost_summary": {
                "step_count": 1,
                "escalated_count": 0,
                "actual_cost": 0.2,
                "baseline_cost": 3.0,
                "savings": 2.8,
            },
            "error": None,
        }
        self.registry_entries = [
            {
                "id": "gemma-coder",
                "tier": 2,
                "endpoint": "https://fireworks.test",
                "capabilities": ["code_complex"],
                "cost": 0.2,
                "privacy": "cloud_ok",
            }
        ]
        self.gate_entries = [
            {"gate_id": "g1", "action": "delete_file", "detail": "delete secrets.txt", "decision": "pending"}
        ]
        self.redaction_log_entries = [
            {"timestamp": "2026-01-01T00:00:00Z", "kind": "email", "matched": "a@b.com"}
        ]
        self.started_goals: list[str] = []
        self.cancelled_run_ids: list[str] = []
        self.registry_updates: list[tuple[str, dict]] = []
        self.gate_resolutions: list[tuple[str, bool]] = []

    async def close(self) -> None:
        pass

    async def list_runs(self) -> list[dict]:
        return self.run_summaries

    async def get_run(self, run_id: str) -> dict:
        return self.run_detail

    async def start_run(self, goal: str) -> dict:
        self.started_goals.append(goal)
        return {"run_id": "r2", "goal": goal, "status": "pending"}

    async def cancel_run(self, run_id: str) -> dict:
        self.cancelled_run_ids.append(run_id)
        return {"run_id": run_id, "goal": "add JWT auth", "status": "cancelled"}

    async def get_registry(self) -> list[dict]:
        return self.registry_entries

    async def update_registry_entry(self, model_id: str, **updates) -> dict:
        self.registry_updates.append((model_id, updates))
        return {**self.registry_entries[0], **updates}

    async def list_gates(self) -> list[dict]:
        return self.gate_entries

    async def resolve_gate(self, gate_id: str, approved: bool) -> dict:
        self.gate_resolutions.append((gate_id, approved))
        return {**self.gate_entries[0], "decision": "approved" if approved else "denied"}

    async def get_redaction_log(self) -> list[dict]:
        return self.redaction_log_entries


async def test_runs_tab_lists_runs_and_shows_detail_on_selection():
    api = _FakeApiClient()
    app = TriarcTUI(api=api)
    async with app.run_test():
        runs_view = app.query_one(RunsView)
        runs_table = runs_view.query_one("#runs-table", DataTable)
        assert runs_table.row_count == 1

        await runs_view.on_data_table_row_selected(
            DataTable.RowSelected(runs_table, cursor_row=0, row_key=RowKey("r1"))
        )

        steps_table = runs_view.query_one("#steps-table", DataTable)
        assert steps_table.row_count == 1
        telemetry_table = runs_view.query_one("#telemetry-table", DataTable)
        assert telemetry_table.row_count == 1


async def test_start_run_button_calls_api_and_clears_input():
    api = _FakeApiClient()
    app = TriarcTUI(api=api)
    async with app.run_test() as pilot:
        runs_view = app.query_one(RunsView)
        goal_input = runs_view.query_one("#goal-input")
        goal_input.value = "add JWT auth to this Flask app"

        start_button = runs_view.query_one("#start-run-btn", Button)
        await runs_view.on_button_pressed(Button.Pressed(start_button))
        await pilot.pause()

        assert api.started_goals == ["add JWT auth to this Flask app"]
        assert goal_input.value == ""


async def test_cancel_button_cancels_selected_run():
    api = _FakeApiClient()
    app = TriarcTUI(api=api)
    async with app.run_test():
        runs_view = app.query_one(RunsView)
        runs_table = runs_view.query_one("#runs-table", DataTable)
        await runs_view.on_data_table_row_selected(
            DataTable.RowSelected(runs_table, cursor_row=0, row_key=RowKey("r1"))
        )

        cancel_button = runs_view.query_one("#cancel-run-btn", Button)
        await runs_view.on_button_pressed(Button.Pressed(cancel_button))

        assert api.cancelled_run_ids == ["r1"]


async def test_registry_tab_lists_entries_and_updates_cost():
    api = _FakeApiClient()
    app = TriarcTUI(api=api)
    async with app.run_test():
        registry_view = app.query_one(RegistryView)
        table = registry_view.query_one("#registry-table", DataTable)
        assert table.row_count == 1

        await registry_view.on_data_table_row_selected(
            DataTable.RowSelected(table, cursor_row=0, row_key=RowKey("gemma-coder"))
        )
        registry_view.query_one("#cost-input").value = "1.5"
        update_button = registry_view.query_one("#update-cost-btn", Button)
        await registry_view.on_button_pressed(Button.Pressed(update_button))

        assert api.registry_updates == [("gemma-coder", {"cost": 1.5})]


async def test_gates_tab_lists_pending_gate_and_approves_it():
    api = _FakeApiClient()
    app = TriarcTUI(api=api)
    async with app.run_test():
        gates_view = app.query_one(GatesView)
        table = gates_view.query_one("#gates-table", DataTable)
        assert table.row_count == 1
        redaction_table = gates_view.query_one("#redaction-log-table", DataTable)
        assert redaction_table.row_count == 1

        await gates_view.on_data_table_row_selected(
            DataTable.RowSelected(table, cursor_row=0, row_key=RowKey("g1"))
        )
        approve_button = gates_view.query_one("#approve-btn", Button)
        await gates_view.on_button_pressed(Button.Pressed(approve_button))

        assert api.gate_resolutions == [("g1", True)]
