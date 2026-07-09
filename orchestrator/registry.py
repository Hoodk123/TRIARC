"""Model registry: single source of model access (architecture.md #3).

Loads configs/models.yaml. No other component may know a model URL or name.
Capability -> endpoint resolution (the routing algorithm) is Phase 1; this module
only loads and looks up entries by id.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel

from orchestrator.schema import Capability, Privacy

_ENV_VAR = re.compile(r"\$\{([A-Z0-9_]+)\}")


class ModelEndpoint(BaseModel):
    id: str
    endpoint: str
    model: str | None = None
    capabilities: list[Capability]
    cost: float
    privacy: Privacy


class ModelRegistry(BaseModel):
    models: list[ModelEndpoint]

    @classmethod
    def load(cls, path: str | Path) -> "ModelRegistry":
        raw = Path(path).read_text()
        resolved = _ENV_VAR.sub(_lookup_env, raw)
        data = yaml.safe_load(resolved)
        return cls.model_validate(data)

    def get(self, model_id: str) -> ModelEndpoint:
        for endpoint in self.models:
            if endpoint.id == model_id:
                return endpoint
        raise KeyError(f"no model registered with id {model_id!r}")


def _lookup_env(match: re.Match[str]) -> str:
    name = match.group(1)
    try:
        return os.environ[name]
    except KeyError as exc:
        raise KeyError(
            f"configs/models.yaml references ${{{name}}}, "
            "but it is not set in the environment"
        ) from exc
