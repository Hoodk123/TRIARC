"""MCP server: fetch + distilled web content (docs/architecture.md #5).

The optional `web` server for lookups (roadmap Phase 5). Fetched pages are external
content, so the result is wrapped as untrusted data before it can enter a model
context (docs/security.md Face 2) -- it is data to read, never instructions to follow.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from orchestrator.security.ingress import wrap_untrusted
from orchestrator.servers.web import ops

mcp = FastMCP("triarc-web")


def _allowlist() -> list[str] | None:
    raw = os.environ.get("TRIARC_WEB_ALLOWLIST")
    return [domain.strip() for domain in raw.split(",") if domain.strip()] if raw else None


@mcp.tool()
def fetch(url: str) -> str:
    """Fetch URL and return its distilled text content, wrapped as untrusted data."""
    content = ops.fetch(url, allowlist=_allowlist())
    return wrap_untrusted(content, source=f"web:{url}")


if __name__ == "__main__":
    mcp.run()
