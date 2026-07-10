"""Async client for the management API (architecture.md #8) -- the TUI is a thin
caller of this one API, the same contract the web client (ui/web/) uses. No routing,
gating, or cost logic lives here; it only reads and forwards.
"""

from __future__ import annotations

import os

import httpx

_DEFAULT_BASE_URL = "http://127.0.0.1:8080"


class ApiClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.environ.get("TRIARC_API_URL", _DEFAULT_BASE_URL)
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def list_runs(self) -> list[dict]:
        response = await self._client.get("/runs")
        response.raise_for_status()
        return response.json()

    async def get_run(self, run_id: str) -> dict:
        response = await self._client.get(f"/runs/{run_id}")
        response.raise_for_status()
        return response.json()

    async def start_run(self, goal: str) -> dict:
        response = await self._client.post("/runs", json={"goal": goal})
        response.raise_for_status()
        return response.json()

    async def cancel_run(self, run_id: str) -> dict:
        response = await self._client.post(f"/runs/{run_id}/cancel")
        response.raise_for_status()
        return response.json()

    async def get_registry(self) -> list[dict]:
        response = await self._client.get("/registry")
        response.raise_for_status()
        return response.json()

    async def update_registry_entry(self, model_id: str, **updates) -> dict:
        response = await self._client.put(f"/registry/{model_id}", json=updates)
        response.raise_for_status()
        return response.json()

    async def list_gates(self) -> list[dict]:
        response = await self._client.get("/gates")
        response.raise_for_status()
        return response.json()

    async def resolve_gate(self, gate_id: str, approved: bool) -> dict:
        response = await self._client.post(f"/gates/{gate_id}/resolve", json={"approved": approved})
        response.raise_for_status()
        return response.json()

    async def get_redaction_log(self) -> list[dict]:
        response = await self._client.get("/redaction-log")
        response.raise_for_status()
        return response.json()
