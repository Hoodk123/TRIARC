import threading
from pathlib import Path

import pytest

from orchestrator.api.run_manager import RunManager, RunNotFoundError, RunStatus
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


class _RaisingTier1Client:
    def plan(self, goal: str) -> Plan:
        raise RuntimeError("boom")


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
            )
        ]
    )


def test_start_run_completes_successfully(tmp_path, monkeypatch):
    plan = Plan(goal="g", steps=[Task(goal="classify", capability_required=Capability.ROUTE)])
    tier1 = _StubTier1Client(plan)
    registry = _minimal_registry()
    manager = RunManager(registry, tier1, tmp_path, sandbox_factory=_StubSandbox)

    class _StubWorker:
        def execute(self, task, feedback=None):
            produced = task.model_copy(update={"confidence": 0.9})
            return ExecutionResult(task=produced, total_tokens=10)

    monkeypatch.setattr(
        "orchestrator.develop_loop.WorkerClient.from_endpoint", lambda endpoint: _StubWorker()
    )

    state = manager.start_run("g")
    final = manager.wait_until_done(state.run_id)

    assert final.status == RunStatus.COMPLETED
    assert len(final.outcomes) == 1
    assert final.outcomes[0].passed is True
    assert len(final.run_log.steps) == 1


def test_cancel_before_any_step_marks_cancelled(tmp_path):
    gate = threading.Event()
    plan = Plan(goal="g", steps=[Task(goal="classify", capability_required=Capability.ROUTE)])
    tier1 = _BlockingTier1Client(plan, gate)
    registry = _minimal_registry()
    manager = RunManager(registry, tier1, tmp_path, sandbox_factory=_StubSandbox)

    state = manager.start_run("g")
    manager.cancel_run(state.run_id)
    gate.set()

    final = manager.wait_until_done(state.run_id)

    assert final.status == RunStatus.CANCELLED
    assert final.outcomes == []


def test_failure_during_routing_marks_failed_with_error(tmp_path):
    registry = _minimal_registry()
    manager = RunManager(registry, _RaisingTier1Client(), tmp_path, sandbox_factory=_StubSandbox)

    state = manager.start_run("g")
    final = manager.wait_until_done(state.run_id)

    assert final.status == RunStatus.FAILED
    assert "boom" in final.error


def test_get_run_raises_for_unknown_id(tmp_path):
    manager = RunManager(_minimal_registry(), _StubTier1Client(Plan(goal="g")), tmp_path)

    with pytest.raises(RunNotFoundError):
        manager.get_run("does-not-exist")


def test_list_runs_returns_all_started_runs(tmp_path):
    gate = threading.Event()
    plan = Plan(goal="g", steps=[])
    manager = RunManager(_minimal_registry(), _BlockingTier1Client(plan, gate), tmp_path, sandbox_factory=_StubSandbox)

    state_a = manager.start_run("goal a")
    state_b = manager.start_run("goal b")
    gate.set()

    manager.wait_until_done(state_a.run_id)
    manager.wait_until_done(state_b.run_id)

    ids = {state.run_id for state in manager.list_runs()}
    assert ids == {state_a.run_id, state_b.run_id}


def test_update_endpoint_mutates_registry_in_place(tmp_path):
    manager = RunManager(_minimal_registry(), _StubTier1Client(Plan(goal="g")), tmp_path)

    updated = manager.update_endpoint("local-router", cost=0.5)

    assert updated.cost == 0.5
    assert manager.registry.get("local-router").cost == 0.5


def test_update_endpoint_raises_for_unknown_id(tmp_path):
    manager = RunManager(_minimal_registry(), _StubTier1Client(Plan(goal="g")), tmp_path)

    with pytest.raises(KeyError):
        manager.update_endpoint("does-not-exist", cost=0.5)
