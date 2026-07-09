"""TRIARC CLI entry point (README quickstart: `triarc run "<goal>"`)."""

from __future__ import annotations

import os

import click

from orchestrator.registry import ModelRegistry
from orchestrator.tier1_client import Tier1Client

_DEFAULT_MODELS_CONFIG = "configs/models.yaml"
_TIER1_MODEL_ID = "local-router"


@click.group()
def cli() -> None:
    """TRIARC -- routes before it reasons."""


@cli.command()
@click.argument("goal")
def run(goal: str) -> None:
    """Route GOAL through Tier 1 and echo the resulting task."""
    config_path = os.environ.get("MODELS_CONFIG", _DEFAULT_MODELS_CONFIG)
    registry = ModelRegistry.load(config_path)
    tier1 = registry.get(_TIER1_MODEL_ID)

    client = Tier1Client(endpoint=tier1.endpoint)
    task = client.route(goal)
    click.echo(task.model_dump_json(indent=2))


if __name__ == "__main__":
    cli()
