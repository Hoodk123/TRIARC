from pathlib import Path

import pytest

from orchestrator.registry import ModelRegistry
from orchestrator.schema import Capability, Privacy

CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "models.yaml"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("LOCAL_ENDPOINT", "http://localhost:8000/v1")
    monkeypatch.setenv("FIREWORKS_GEMMA_MODEL", "accounts/fireworks/models/gemma-test")
    monkeypatch.setenv("FIREWORKS_LARGE_MODEL", "accounts/fireworks/models/large-test")


def test_loads_configs_models_yaml():
    registry = ModelRegistry.load(CONFIG_PATH)

    local = registry.get("local-router")
    assert local.endpoint == "http://localhost:8000/v1"
    assert local.privacy == Privacy.LOCAL
    assert Capability.ROUTE in local.capabilities


def test_missing_env_var_raises(monkeypatch):
    monkeypatch.delenv("LOCAL_ENDPOINT", raising=False)

    with pytest.raises(KeyError, match="LOCAL_ENDPOINT"):
        ModelRegistry.load(CONFIG_PATH)


def test_unknown_model_id_raises():
    registry = ModelRegistry.load(CONFIG_PATH)

    with pytest.raises(KeyError):
        registry.get("does-not-exist")
