"""Response/request models for the management API (architecture.md #8).

Thin Pydantic wrappers around the internal dataclasses in run_manager.py and
telemetry.py -- kept separate so the wire format can evolve without touching the
run-execution machinery.
"""

from __future__ import annotations

from pydantic import BaseModel

from orchestrator.schema import Capability, Privacy, Task


class StartRunRequest(BaseModel):
    goal: str


class RunSummaryOut(BaseModel):
    run_id: str
    goal: str
    status: str


class RoutedStepOut(BaseModel):
    endpoint_id: str
    task: Task


class StepOutcomeOut(BaseModel):
    task_id: str
    attempts: int
    passed: bool
    escalations: list[str]


class StepLogOut(BaseModel):
    task_id: str
    goal: str
    tier: int | None
    endpoint_id: str
    tokens: int
    cost: float
    confidence: float
    escalated: bool
    passed: bool | None


class CostSummaryOut(BaseModel):
    step_count: int
    escalated_count: int
    actual_cost: float
    baseline_cost: float
    savings: float


class RunOut(BaseModel):
    run_id: str
    goal: str
    status: str
    routed_steps: list[RoutedStepOut]
    outcomes: list[StepOutcomeOut]
    telemetry: list[StepLogOut]
    cost_summary: CostSummaryOut | None
    error: str | None


class ModelEndpointUpdate(BaseModel):
    endpoint: str | None = None
    model: str | None = None
    capabilities: list[Capability] | None = None
    cost: float | None = None
    privacy: Privacy | None = None
    tier: int | None = None


class GateOut(BaseModel):
    gate_id: str
    action: str
    detail: str
    decision: str


class ResolveGateRequest(BaseModel):
    approved: bool
