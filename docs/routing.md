# Routing & Escalation

The heart of TRIARC. This document specifies how a goal becomes routed sub-tasks and how
escalation works. It expands on [architecture.md §3–4](architecture.md).

## The routing contract

The orchestrator **never names a model.** It emits a capability requirement and
constraints; the registry resolves them. This single rule is what keeps the system
swappable and is the source of the cost win.

```
orchestrator  ──emits──▶  { capability_required, constraints }
registry      ──resolves─▶  cheapest endpoint where
                              capabilities ⊇ required
                              AND privacy satisfies constraints
                              AND cost ≤ constraints.max_cost (if set)
```

## Capabilities

| Capability | Meaning | Typical tier |
|---|---|---|
| `route` | classify / decompose a goal | Tier 1 |
| `extract` | pull structured data from text | Tier 1 |
| `code_simple` | small edits, boilerplate, single-function code | Tier 1 / 2 |
| `tool_use` | pick and call an MCP tool | Tier 2 |
| `code_complex` | multi-file features, non-trivial logic | Tier 2 |
| `debug` | diagnose a failing test / subtle bug | Tier 3 |
| `synthesis` | open-ended design / cross-file reasoning | Tier 3 |

## Resolution algorithm

1. Filter registry endpoints to those whose `capabilities` superset the requirement.
2. Drop endpoints that violate the task's `privacy` constraint (a `privacy: local` task
   can never resolve to a cloud endpoint).
3. Drop endpoints above `constraints.max_cost` if set.
4. Among survivors, pick the **cheapest** (ties broken by lowest latency).
5. If none survive, escalate the capability requirement one level and retry.

## Escalation ladder

Escalation happens in two ways:

**A. Predictive (at routing time).** The orchestrator's plan may mark a step as needing a
higher capability up front (e.g. it recognizes a refactor as `code_complex`, not
`code_simple`).

**B. Reactive (fail-upward).** A step returns with low `confidence` or an explicit
`escalation_reason`. TRIARC re-routes the same task one tier up, carrying the failed
attempt and any error output as context so the stronger model doesn't start cold.

```
Tier 1 (local)  ──low confidence / escalation_reason──▶  Tier 2 (Gemma)
Tier 2 (Gemma)  ──low confidence / escalation_reason──▶  Tier 3 (large)
Tier 3          ──still failing──▶  surface to the user with the full attempt trail
```

Every escalation is logged with its reason, so a run's escalation history is inspectable.

## Why "never a model name"

If the orchestrator emitted `"use gemma"`, then swapping models would require retraining
or rewriting the orchestrator. By emitting `"code_complex"` instead, the registry absorbs
all model churn. In the original from-scratch system this is what let the orchestrator
adapter stay valid across model upgrades; here it's what lets you swap Fireworks models
with a one-line YAML edit.

## Cost accounting

Each resolved call records `{tier, endpoint, tokens, cost, confidence, escalated}`. The
run summary computes:

- **actual cost** = Σ per-step cost
- **baseline cost** = same steps if every one had been routed to the largest model
- **savings** = baseline − actual

This comparison is the demo's money-shot and the clearest evidence for the Track-3
cost-efficiency argument.
