# TRIARC — Feature Documentation

What TRIARC does, feature by feature. Each entry states the capability, how it works,
and which tier(s) it uses. This is the "what you get" companion to
[architecture.md](architecture.md) (the "how it's built").

---

## 1. Autonomous develop loop

**What it does.** Give TRIARC a natural-language goal and it runs the full loop:
plan → route → execute → test → read failures → fix → repeat, until the goal is met or
it hits a gate that needs you.

**How it works.**
1. The orchestrator decomposes the goal into an ordered plan of sub-tasks.
2. Each sub-task is emitted as a task-schema instance with a `capability_required`.
3. The registry routes each step to the cheapest capable model.
4. Code runs in a sandboxed container; tests run; failures are read back into context.
5. The loop continues, escalating only the steps that genuinely need a stronger model.

**Tiers used.** All three, per step — most steps resolve to Tier 1 or 2.

**Example.** `"add JWT auth to this Flask app and write tests"` → plan (Tier 1) →
scaffold routes and middleware (Tier 2/Gemma) → write tests (Tier 2) → run tests
(sandbox) → a subtle token-expiry bug fails → escalate the fix (Tier 3) → tests pass.

---

## 2. Capability-based routing

**What it does.** Sends every step to the cheapest model that can actually do it,
instead of pushing everything through one large model.

**How it works.** The orchestrator emits a **capability requirement**
(`route | extract | code_simple | code_complex | tool_use | research | synthesis | debug`),
never a model name. The registry resolves it to an endpoint using a capability profile
(what it can do, cost, privacy, latency). Adding or upgrading a model is a config edit.

**Why it matters.** This is the cost engine. It's also the moat: the same insight Track 1
of this hackathon rewards, applied to a real product.

**Tiers used.** The router itself is Tier 1; it dispatches to all tiers.

---

## 3. Fail-upward escalation (no bluffing)

**What it does.** When a step exceeds the current model's ability, TRIARC escalates to a
stronger tier instead of returning a confident-but-wrong answer.

**How it works.** Every task result carries a mandatory `confidence` value and an
`escalation_reason` path. Low confidence or an explicit "this needs a bigger model"
signal triggers re-routing one tier up. Escalation reasons are logged, so you can see
*why* each escalation happened.

**Why it matters.** Overconfidence is the #1 reliability complaint about coding agents.
A first-class, trained way to say "I can't do this alone" is the fix.

---

## 4. Structured, schema-enforced decisions

**What it does.** Guarantees that routing and tool-call decisions are always valid,
machine-readable structures — never free text the pipeline has to guess at.

**How it works.** All control-flow decisions use grammar/JSON-schema-constrained
decoding. Inter-agent messages are schema-validated at every hop. The dominant failure
mode of multi-agent systems is silent misinterpretation between agents; rigid schemas +
validation is the defense.

**The task schema (single source of truth):**

```json
{
  "task_id": "uuid",
  "goal": "string",
  "capability_required": "route|extract|code_simple|code_complex|tool_use|research|synthesis|debug",
  "context_refs": ["file or corpus references, never inlined blobs"],
  "constraints": {"privacy": "local|cloud_ok", "max_cost": 0},
  "result": null,
  "confidence": 0.0,
  "escalation_reason": null
}
```

---

## 5. Sandboxed code execution

**What it does.** Runs all model-written code in an isolated container, so an agent can
execute and test its own work without touching your host.

**How it works.** Rootless containers, no network by default (per-task opt-in +
allowlist), workspace-scoped mounts, resource limits, and timeouts. Sandbox-escape
attempts and denied syscalls are logged and surfaced.

**Tiers used.** Any — the sandbox is a tool, not a model.

---

## 6. MCP tool layer (pluggable skills)

**What it does.** Lets TRIARC use tools — git, filesystem, web, code sandbox — and lets
you add new ones without changing TRIARC's code.

**How it works.** Every capability is an **MCP server**. The existing public MCP catalog
(git, GitHub, filesystem, databases, browser automation, etc.) works day one; you add a
skill by listing an MCP server in config. First-party servers shipped with TRIARC:

- **code-sandbox** — containerized execution (feature 5)
- **git** — clone, branch, diff, commit
- **filesystem** — scoped read/write within the workspace
- **web** — fetch + distilled page content for lookups

**Two-stage tool selection.** With many servers connected, tool definitions would flood a
small model's context. Stage 1: classify to a server/category. Stage 2: only that
server's tools enter context for the actual call.

---

## 7. Three-faced security plane

**What it does.** Protects against secret leakage, prompt injection, and unauthorized
irreversible actions — automatically, on every step.

**How it works** (full detail in [security.md](security.md)):

- **Egress** — secrets, keys, paths, and PII are redacted before any payload reaches a
  cloud (Tier 3) endpoint. A local redaction log lets you audit exactly what left.
- **Ingress** — all external content (web pages, tool results, file contents) is wrapped
  in tagged untrusted-data blocks. It is data to transform, never instructions to follow.
- **Confirmation gates** — every irreversible action (code exec outside the sandbox, file
  deletion, sending messages, spending money) pauses for explicit confirmation, for
  every actor, every time.

---

## 8. Cost telemetry & transparency

**What it does.** Shows, per run, which tier answered each step and how many tokens each
Fireworks call cost — plus a "vs. all-frontier baseline" comparison.

**How it works.** Every task logs its chosen tier, endpoint, token count, and outcome.
The run summary aggregates these into a cost tally and a savings figure against a
hypothetical "route everything to the biggest model" baseline.

**Why it matters.** This is the demo's strongest Track-3 argument: the cost win is
measured and shown, not asserted. (It also becomes routing-quality training data if you
later revive the from-scratch orchestrator adapter.)

---

## 9. Backend-agnostic model registry

**What it does.** Lets you point any tier at any OpenAI-compatible endpoint — local model
on AMD hardware, Fireworks, or anything else — through config alone.

**How it works.** `configs/models.yaml` lists endpoints with capability profiles. The
registry is the single source of model access; no other component knows a model URL or
name. Consequences: upgrade a model = config change, zero code change; add a new provider
without touching the router.

```yaml
models:
  - id: local-router
    endpoint: http://amd-pod:8000/v1
    capabilities: [route, extract, code_simple]
    cost: 0
    privacy: local
  - id: gemma-coder
    endpoint: https://api.fireworks.ai/inference/v1
    model: accounts/fireworks/models/gemma-...
    capabilities: [code_complex, tool_use]
    cost: low
    privacy: cloud_ok
  - id: frontier
    endpoint: https://api.fireworks.ai/inference/v1
    model: accounts/fireworks/models/<large>
    capabilities: [synthesis, debug, reasoning_deep]
    cost: high
    privacy: cloud_ok
```

---

## 10. Management UI (web + TUI)

**What it does.** Gives you a live dashboard over a running TRIARC instance — in the
browser or in the terminal — for the four things an operator actually needs mid-run:
run monitoring, cost/routing telemetry, model registry config, and confirmation gates.

**How it works.**
1. `orchestrator/api/` exposes a single **management API** (REST for reads/mutations,
   WebSocket for live push) over the orchestrator's existing state: run/task status
   (feature 1), per-step cost log (feature 8), `configs/models.yaml` (feature 9), and
   pending confirmation gates (feature 7).
2. Two thin clients consume the same API — no logic lives in either client that isn't
   already in the orchestrator:
   - **Web** (`ui/web/`) — a browser dashboard for the same four views, better suited to
     wide telemetry tables and charts.
   - **TUI** (`ui/tui/`) — a terminal dashboard for the same four views, for operators
     working over SSH or who never leave the terminal.
3. Views:
   - **Run monitoring & control** — live goal → plan → per-step status; start/cancel a
     run.
   - **Cost & routing telemetry** — per-step tier/endpoint/tokens/cost, escalation
     history, actual-vs-baseline savings (the feature-8 numbers, rendered).
   - **Model registry editor** — view/edit registry entries (endpoint, capabilities,
     cost, privacy) without hand-editing YAML.
   - **Confirmation gate inbox** — approve/deny pending irreversible actions; view the
     egress redaction log.

**Why it matters.** The routing and escalation story (features 2–3) and the cost win
(feature 8) are only compelling if you can actually see them happen, live, without
tailing raw logs. The gate inbox also gives face 3 of the security plane (security.md) a
real UI instead of a blocking terminal prompt.

**Tiers used.** None — this is a pure UI/API layer over existing orchestrator state, not
a model consumer. It must not gain its own routing or gate-bypass logic; see
architecture.md §8.

---

## Feature-to-tier summary

| Feature | Primary tier | Notes |
|---|---|---|
| Autonomous develop loop | all | orchestrated per step |
| Capability-based routing | Tier 1 dispatches | the cost engine |
| Fail-upward escalation | crosses tiers | confidence + escalation_reason |
| Structured decisions | Tier 1 | schema-constrained decode |
| Sandboxed execution | tool (any) | rootless container |
| MCP tool layer | tool (any) | two-stage selection |
| Security plane | every hop | egress / ingress / gates |
| Cost telemetry | orchestrator | the demo money-shot |
| Model registry | orchestrator | backend-agnostic |
| Management UI (web + TUI) | none (UI/API layer) | thin clients over one management API |
