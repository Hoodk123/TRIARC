"""TRIARC CLI entry point (README quickstart: `triarc run "<goal>"`)."""

from __future__ import annotations
from orchestrator.worker_client import WorkerClient
from orchestrator.registry import escalate_capability, NoCapableEndpointError


import json
import os

import click

from orchestrator.develop_loop import run_plan
from orchestrator.planner import route_plan
from orchestrator.registry import ModelRegistry
from orchestrator.report import print_run_report
from orchestrator.servers.code_sandbox.runtime import ContainerRuntime
from orchestrator.telemetry import RunLog
from orchestrator.tier1_client import Tier1Client

_DEFAULT_MODELS_CONFIG = "configs/models.yaml"
_DEFAULT_WORKSPACE = "."
_TIER1_MODEL_ID = "local-router"

_CONFIDENCE_THRESHOLD = 0.5
_MAX_ESCALATIONS = 2

@click.group()
def cli() -> None:
    """TRIARC -- routes before it reasons."""


@cli.command()
@click.argument("goal")
@click.option(
    "--execute/--no-execute",
    default=False,
    help="Run the test-run-read-fix loop after routing "
    "(requires Docker and live Tier 2/3 endpoints).",
)
def run(goal: str, execute: bool) -> None:
    """Decompose GOAL into a routed plan and echo each step's resolved endpoint."""
    config_path = os.environ.get("MODELS_CONFIG", _DEFAULT_MODELS_CONFIG)
    registry = ModelRegistry.load(config_path)
    tier1 = registry.get(_TIER1_MODEL_ID)

    client = Tier1Client(endpoint=tier1.endpoint, model=tier1.model or "tier1-router")
    routed_steps = route_plan(goal, client, registry)
    click.echo(
        json.dumps(
            [
                {"endpoint": step.endpoint.id, "task": step.task.model_dump()}
                for step in routed_steps
            ],
            indent=2,
        )
    )

    if not execute:
        return

    workspace = os.environ.get("TRIARC_WORKSPACE", _DEFAULT_WORKSPACE)
    sandbox = ContainerRuntime(workspace)
    run_log = RunLog()
    outcomes = run_plan(routed_steps, registry, sandbox, run_log=run_log)
    click.echo(
        json.dumps(
            [
                {
                    "task_id": outcome.task_id,
                    "attempts": outcome.attempts,
                    "passed": outcome.passed,
                    "escalations": outcome.escalations,
                }
                for outcome in outcomes
            ],
            indent=2,
        )
    )

    if run_log.steps:
        largest_cost = max(endpoint.cost for endpoint in registry.models)
        print_run_report(run_log, run_log.summary(largest_cost))


@cli.command()
@click.option("--host", default="127.0.0.1", help="Bind address for the management API.")
@click.option("--port", default=8080, type=int, help="Bind port for the management API.")
def serve(host: str, port: int) -> None:
    """Serve the management API (architecture.md #8) for the web/TUI clients."""
    import uvicorn

    from orchestrator.api.app import create_app

    uvicorn.run(create_app(), host=host, port=port)

def _next_stronger_endpoint(registry, capability, constraints, current_cost, tried_ids):
    candidates = [
        e for e in registry.models
        if capability in e.capabilities
        and e.id not in tried_ids
        and e.cost > current_cost
        and (constraints.max_cost is None or e.cost <= constraints.max_cost)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda e: e.cost)

@cli.command(name="run-task")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--output", "output_path", required=True, type=click.Path())
def run_task(input_path: str, output_path: str) -> None:
    config_path = os.environ.get("MODELS_CONFIG", _DEFAULT_MODELS_CONFIG)
    registry = ModelRegistry.load(config_path)
    tier1 = registry.get(_TIER1_MODEL_ID)
    client = Tier1Client(endpoint=tier1.endpoint, model=tier1.model or "tier1-router")

    with open(input_path) as f:
        raw_tasks = json.load(f)

    results = []
    for raw in raw_tasks:
        goal = raw["goal"]
        task_id = raw.get("task_id", "")

        try:
            task = client.route(goal)  # single classification, goal preserved verbatim
            endpoint = registry.resolve(task.capability_required, task.constraints)

            tried = set()
            produced = None
            for _ in range(_MAX_ESCALATIONS + 1):
                tried.add(endpoint.id)
                worker = WorkerClient.from_endpoint(endpoint)
                exec_result = worker.execute(task)
                produced = exec_result.task
                if produced.confidence >= _CONFIDENCE_THRESHOLD or produced.escalation_reason is None:
                    break
                next_endpoint = _next_stronger_endpoint(registry, task.capability_required, task.constraints, endpoint.cost, tried)
                if next_endpoint is None:
                    break
                endpoint = next_endpoint

            results.append({"task_id": task_id, "goal": goal, "result": produced.result, "confidence": produced.confidence})
        except Exception as exc:
            results.append({"task_id": task_id, "goal": goal, "result": None, "confidence": 0.0, "error": str(exc)})

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    cli()
