"""In-memory run orchestration for the management API (architecture.md #8; roadmap
Phase 4). Runs the same route_plan + develop_loop machinery Phases 1-3 already built,
in a background thread, and stores per-run state so the web/TUI clients can poll or
watch progress over one shared API -- this module owns no routing, gating, or cost
logic of its own; it only calls into the existing pipeline.
"""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from orchestrator.develop_loop import StepOutcome, run_step
from orchestrator.planner import RoutedStep, route_plan
from orchestrator.registry import ModelEndpoint, ModelRegistry
from orchestrator.security.gates import ConfirmationGateRegistry
from orchestrator.servers.code_sandbox.runtime import ContainerRuntime
from orchestrator.telemetry import RunLog
from orchestrator.tier1_client import Tier1Client


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}


@dataclass
class RunState:
    run_id: str
    goal: str
    status: RunStatus = RunStatus.PENDING
    routed_steps: list[RoutedStep] = field(default_factory=list)
    outcomes: list[StepOutcome] = field(default_factory=list)
    run_log: RunLog = field(default_factory=RunLog)
    error: str | None = None
    cancel_requested: bool = False


class RunNotFoundError(KeyError):
    pass


class RunManager:
    """Starts and tracks runs; the FastAPI app (orchestrator/api/app.py) is a thin
    wrapper over this -- it forwards requests here and serializes the result."""

    def __init__(
        self,
        registry: ModelRegistry,
        tier1: Tier1Client,
        workspace: str | Path,
        *,
        sandbox_factory=ContainerRuntime,
        max_workers: int = 4,
    ) -> None:
        self._registry = registry
        self._tier1 = tier1
        self._workspace = workspace
        self._sandbox_factory = sandbox_factory
        self._runs: dict[str, RunState] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="triarc-run")
        self._gates = ConfirmationGateRegistry()

    @property
    def registry(self) -> ModelRegistry:
        return self._registry

    @property
    def gates(self) -> ConfirmationGateRegistry:
        return self._gates

    def start_run(self, goal: str) -> RunState:
        run_id = str(uuid.uuid4())
        state = RunState(run_id=run_id, goal=goal)
        with self._lock:
            self._runs[run_id] = state
        self._executor.submit(self._execute, run_id)
        return state

    def get_run(self, run_id: str) -> RunState:
        with self._lock:
            try:
                return self._runs[run_id]
            except KeyError:
                raise RunNotFoundError(run_id) from None

    def list_runs(self) -> list[RunState]:
        with self._lock:
            return list(self._runs.values())

    def cancel_run(self, run_id: str) -> RunState:
        state = self.get_run(run_id)
        with self._lock:
            if state.status in (RunStatus.PENDING, RunStatus.RUNNING):
                state.cancel_requested = True
        return state

    def update_endpoint(self, model_id: str, **updates) -> ModelEndpoint:
        with self._lock:
            endpoint = self._registry.get(model_id)
            index = self._registry.models.index(endpoint)
            updated = endpoint.model_copy(update=updates)
            self._registry.models[index] = updated
            return updated

    def wait_until_done(self, run_id: str, timeout: float = 5.0) -> RunState:
        """Block until RUN_ID reaches a terminal status. For tests/CLI convenience --
        the API itself never blocks on this; clients poll GET or the websocket."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.get_run(run_id)
            if state.status in TERMINAL_STATUSES:
                return state
            time.sleep(0.01)
        raise TimeoutError(f"run {run_id!r} did not finish within {timeout}s")

    def _execute(self, run_id: str) -> None:
        state = self.get_run(run_id)
        try:
            with self._lock:
                state.status = RunStatus.RUNNING

            routed_steps = route_plan(state.goal, self._tier1, self._registry)
            with self._lock:
                state.routed_steps = routed_steps

            sandbox = self._sandbox_factory(self._workspace)
            for step in routed_steps:
                with self._lock:
                    if state.cancel_requested:
                        state.status = RunStatus.CANCELLED
                        return

                outcome = run_step(step, self._registry, sandbox, run_log=state.run_log)

                with self._lock:
                    state.outcomes.append(outcome)
                    if not outcome.passed:
                        state.status = RunStatus.FAILED
                        return

            with self._lock:
                state.status = RunStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001 -- the API surfaces the failure; a
            # background thread with no other listener must not fail silently.
            with self._lock:
                state.status = RunStatus.FAILED
                state.error = str(exc)
