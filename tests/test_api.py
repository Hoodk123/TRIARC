import threading
from pathlib import Path

from fastapi.testclient import TestClient

from orchestrator.api.app import create_app
from orchestrator.api.run_manager import RunManager
from orchestrator.registry import ModelEndpoint, ModelRegistry
from orchestrator.schema import Capability, Plan, Privacy, Task
from orchestrator.servers.code_sandbox.runtime import SandboxResult
from orchestrator.worker_client import ExecutionResult


class _StubTier1Client:
    def __init__(self, plan: Plan) -> None:
        self._plan = plan

    def plan(self, goal: str) -> Plan:
        return self._plan


class _BlockingTier1Client:
    def __init__(self, plan: Plan, gate: threading.Event) -> None:
        self._plan = plan
        self._gate = gate

    def plan(self, goal: str) -> Plan:
        self._gate.wait(timeout=5)
        return self._plan


class _StubSandbox:
    def __init__(self, workspace) -> None:
        self.workspace = Path(workspace)

    def run(self, command):
        return SandboxResult(exit_code=0, stdout="1 passed", stderr="")


def _minimal_registry() -> ModelRegistry:
    return ModelRegistry(
        models=[
            ModelEndpoint(
                id="local-router",
                endpoint="http://local:8000/v1",
                capabilities=[Capability.ROUTE],
                cost=0,
                privacy=Privacy.LOCAL,
                tier=1,
            ),
            ModelEndpoint(
                id="frontier",
                endpoint="https://fireworks.test/v1",
                capabilities=[Capability.SYNTHESIS],
                cost=3.0,
                privacy=Privacy.CLOUD_OK,
                tier=3,
            ),
        ]
    )


def _client_with_completing_run(monkeypatch, tmp_path):
    plan = Plan(goal="g", steps=[Task(goal="classify", capability_required=Capability.ROUTE)])
    manager = RunManager(_minimal_registry(), _StubTier1Client(plan), tmp_path, sandbox_factory=_StubSandbox)

    class _StubWorker:
        def execute(self, task, feedback=None):
            produced = task.model_copy(update={"confidence": 0.9})
            return ExecutionResult(task=produced, total_tokens=10)

    monkeypatch.setattr(
        "orchestrator.develop_loop.WorkerClient.from_endpoint", lambda endpoint: _StubWorker()
    )
    return TestClient(create_app(manager)), manager


def test_post_runs_returns_run_id_immediately(monkeypatch, tmp_path):
    client, _ = _client_with_completing_run(monkeypatch, tmp_path)

    response = client.post("/runs", json={"goal": "add JWT auth"})

    assert response.status_code == 202
    body = response.json()
    assert body["goal"] == "add JWT auth"
    assert "run_id" in body


def test_get_run_reports_completed_status_with_telemetry(monkeypatch, tmp_path):
    client, manager = _client_with_completing_run(monkeypatch, tmp_path)
    run_id = client.post("/runs", json={"goal": "add JWT auth"}).json()["run_id"]
    manager.wait_until_done(run_id)

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["outcomes"]) == 1
    assert body["outcomes"][0]["passed"] is True
    assert len(body["telemetry"]) == 1
    assert body["cost_summary"]["step_count"] == 1


def test_get_unknown_run_returns_404(monkeypatch, tmp_path):
    client, _ = _client_with_completing_run(monkeypatch, tmp_path)

    response = client.get("/runs/does-not-exist")

    assert response.status_code == 404


def test_list_runs_includes_started_run(monkeypatch, tmp_path):
    client, manager = _client_with_completing_run(monkeypatch, tmp_path)
    run_id = client.post("/runs", json={"goal": "add JWT auth"}).json()["run_id"]
    manager.wait_until_done(run_id)

    response = client.get("/runs")

    assert response.status_code == 200
    assert any(run["run_id"] == run_id for run in response.json())


def test_cancel_run_before_it_starts_marks_cancelled(tmp_path):
    gate = threading.Event()
    plan = Plan(goal="g", steps=[Task(goal="classify", capability_required=Capability.ROUTE)])
    manager = RunManager(
        _minimal_registry(), _BlockingTier1Client(plan, gate), tmp_path, sandbox_factory=_StubSandbox
    )
    client = TestClient(create_app(manager))

    run_id = client.post("/runs", json={"goal": "add JWT auth"}).json()["run_id"]
    cancel_response = client.post(f"/runs/{run_id}/cancel")
    gate.set()
    final = manager.wait_until_done(run_id)

    assert cancel_response.status_code == 200
    assert final.status.value == "cancelled"


def test_get_registry_lists_configured_endpoints(monkeypatch, tmp_path):
    client, _ = _client_with_completing_run(monkeypatch, tmp_path)

    response = client.get("/registry")

    assert response.status_code == 200
    ids = {entry["id"] for entry in response.json()}
    assert ids == {"local-router", "frontier"}


def test_put_registry_updates_endpoint(monkeypatch, tmp_path):
    client, manager = _client_with_completing_run(monkeypatch, tmp_path)

    response = client.put("/registry/frontier", json={"cost": 5.0})

    assert response.status_code == 200
    assert response.json()["cost"] == 5.0
    assert manager.registry.get("frontier").cost == 5.0


def test_put_registry_unknown_model_returns_404(monkeypatch, tmp_path):
    client, _ = _client_with_completing_run(monkeypatch, tmp_path)

    response = client.put("/registry/does-not-exist", json={"cost": 5.0})

    assert response.status_code == 404


def test_gates_list_starts_empty(monkeypatch, tmp_path):
    client, _ = _client_with_completing_run(monkeypatch, tmp_path)

    response = client.get("/gates")

    assert response.status_code == 200
    assert response.json() == []


def test_resolve_unknown_gate_returns_404(monkeypatch, tmp_path):
    client, _ = _client_with_completing_run(monkeypatch, tmp_path)

    response = client.post("/gates/does-not-exist/resolve", json={"approved": True})

    assert response.status_code == 404


def test_redaction_log_reads_local_log_file(monkeypatch, tmp_path):
    client, _ = _client_with_completing_run(monkeypatch, tmp_path)
    log_path = tmp_path / "redaction.log"
    log_path.write_text('{"timestamp": "t", "kind": "email", "matched": "a@b.com"}\n')
    monkeypatch.setenv("TRIARC_REDACTION_LOG", str(log_path))

    response = client.get("/redaction-log")

    assert response.status_code == 200
    assert response.json() == [{"timestamp": "t", "kind": "email", "matched": "a@b.com"}]


def test_redaction_log_empty_when_no_log_file_yet(monkeypatch, tmp_path):
    client, _ = _client_with_completing_run(monkeypatch, tmp_path)
    monkeypatch.setenv("TRIARC_REDACTION_LOG", str(tmp_path / "does-not-exist.log"))

    response = client.get("/redaction-log")

    assert response.status_code == 200
    assert response.json() == []


def test_websocket_streams_run_state_until_terminal(monkeypatch, tmp_path):
    client, _ = _client_with_completing_run(monkeypatch, tmp_path)
    run_id = client.post("/runs", json={"goal": "add JWT auth"}).json()["run_id"]

    with client.websocket_connect(f"/runs/{run_id}/ws") as ws:
        final_status = None
        for _ in range(50):
            message = ws.receive_json()
            final_status = message["status"]
            if final_status in ("completed", "failed", "cancelled"):
                break

    assert final_status == "completed"
