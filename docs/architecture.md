# TRIARC System Architecture

Status: **hackathon build**. TRIARC keeps the abstractions of the original tri-agent
system and swaps the model layer for online LLMs on AMD/Fireworks. Additions must slot
into an existing abstraction; new abstractions require updating this document first.

## 1. Overview

TRIARC is a layered, routing-first autonomous developer. A small orchestrator model
handles classification, decomposition, and routing locally (Tier 1 on the AMD GPU pod).
Harder sub-tasks escalate through a model registry to Fireworks-hosted models (Tiers 2–3).

Layers, top to bottom:

1. **Entry point** — CLI / local API (`triarc run "<goal>"`)
2. **Orchestrator core** — router/planner loop + security plane
3. **Model registry** — pluggable OpenAI-compatible endpoints in three tiers
4. **Tool layer** — everything is an MCP server
5. **Workspace** — sandboxed project directory + run/telemetry logs

## 2. The model layer: one router, three tiers

In the original system, one ~0.8B base model was specialized into three roles via LoRA
adapters, all running locally. TRIARC preserves the **roles and routing contract** but
maps them onto hosted endpoints so the product ships in the hackathon window:

| Role (original) | TRIARC realization | Endpoint |
|---|---|---|
| Orchestrator (router/planner) | small model, constrained JSON decode | Tier 1, local on AMD GPU pod |
| Agent (tool/code executor) | structured coding + tool calls | Tier 2, Fireworks (Gemma) |
| Escalation target (deep reasoning) | multi-file refactor, subtle debug | Tier 3, Fireworks large |

The routing **contract is unchanged**: the orchestrator emits a required capability, and
the registry resolves it to the cheapest endpoint satisfying capability + privacy + cost.

### 2.1 Capability boundaries (honest limits)

The Tier-1 router performs: classification, routing, extraction, filling structured
plans, simple code edits. It does NOT perform: open-ended synthesis, cross-file
reasoning, or subtle debugging — those are escalation triggers by design, exactly as in
the original design's honest capability boundaries.

## 3. Model registry

Single source of model access. Every endpoint registers a capability profile. The
orchestrator emits `capability_required` + constraints (never a model name); the registry
resolves to the cheapest endpoint satisfying capability + privacy + cost. Consequences:

- Adding/upgrading a model = config change, zero code change.
- Tier-3 (cloud) requires `constraints.privacy == cloud_ok` AND passes the egress
  gatekeeper (see [security.md](security.md)).

See [features.md §9](features.md) for the YAML shape and
[routing.md](routing.md) for resolution mechanics.

## 4. Orchestrator core

- **Router/planner loop:** request → orchestrator (constrained JSON decode) → task
  schema instance → registry resolution → worker invocation → result assembly → loop.
- **Task schema** (versioned; single source `orchestrator/schema.py`):
  `{task_id, goal, capability_required, context_refs, constraints, result, confidence,
  escalation_reason}`. `confidence` + `escalation_reason` are mandatory — the mechanism
  by which the system fails upward instead of bluffing.
- **Two-stage tool selection:** classify to a server/category first; only that server's
  tools enter context for the actual call. Keeps a small router's context clean.
- **Inter-agent messages are schema-validated** at every hop — the defense against silent
  misinterpretation between agents.
- **Async task semantics:** immediate ack, progress events, result delivery keyed by
  `task_id` (long-running develop loops are the norm).

## 5. Tool layer (MCP)

Adopt MCP outright; do not invent a plugin format. First-party servers:
**code-sandbox** (containerized execution), **git**, **filesystem** (workspace-scoped),
**web** (fetch + distilled content). Users add skills by listing MCP servers in config.

## 6. Workspace & telemetry

- **Workspace:** the project directory the agent operates on, mounted into the sandbox
  with scoped permissions.
- **Run log:** per-step record of chosen tier, endpoint, token count, outcome, and any
  escalation reason. Aggregated into the cost tally (features.md §8) and — if you later
  revive the from-scratch orchestrator adapter — routing-quality training data, exactly
  as Phase 4 of the original roadmap intended.

## 7. Invariants (checked in review)

- No component other than the registry knows a model URL or name.
- No tool exists that can modify security policy or confirmation-gate behavior.
- No free-text parsing for control flow anywhere.
- Every irreversible action passes a confirmation gate.
- Every payload to a Tier-3 endpoint passes the egress gatekeeper.
- Every external content path is wrapped as untrusted before entering a model.
