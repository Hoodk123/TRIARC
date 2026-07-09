# TRIARC — The Autonomous AI Developer That Routes Before It Reasons

**AMD Developer Hackathon: ACT II — Track 3 (Unicorn Track 🦄)**

TRIARC is an autonomous AI developer that plans, writes, runs, and debugs code by
routing every step to the *cheapest capable model* — free local inference first,
Fireworks-hosted models only when the task actually demands it. A small orchestrator
decides **who** does the work; large models are called on demand, never by default.

The name comes from the **tri-agent architecture** at its core: one orchestrator that
routes, plus the reasoning tiers it escalates to — three roles, one arc from plan to
shipped code.

> **Lineage.** TRIARC is the hackathon incarnation of a from-scratch, local-first
> personal AI system built on three LoRA-specialized roles (Orchestrator, Agent,
> Researcher). The fundamentals are identical — capability-based routing, an escalation
> ladder, schema-enforced inter-agent messages, MCP tools, a three-faced security plane.
> For the hackathon the custom local models are swapped for online LLMs served through
> **Fireworks AI on AMD infrastructure**, so the full product could be built inside the
> event window.

---

## The problem

Autonomous coding agents are expensive and brittle. Most push every step — trivial file
edits, boilerplate, simple lookups — through a large frontier model, burning tokens on
work a tiny model could do, and they bluff confidently when a task exceeds their reach
instead of escalating. **Cost scales with ambition, and reliability doesn't.**

TRIARC's answer is to separate *orchestration* from *reasoning*:

- A small, fast **orchestrator** does only classification, decomposition, and routing.
  It never attempts open-ended synthesis.
- For each sub-task it emits a required **capability** (never a model name).
- A **registry** resolves that capability to the cheapest endpoint that satisfies it.
- Every result carries a `confidence` score and an `escalation_reason` — the system
  **fails upward instead of bluffing.**

---

## The three tiers (routing contract)

The orchestrator emits `capability_required`; the registry resolves it to an endpoint.
No component ever hardcodes a model name — swapping a model is a one-line config change.

| Tier | Endpoint | Handles | Cost |
|---|---|---|---|
| **Tier 1** | Local model on the AMD GPU pod | classification, extraction, simple edits, routing | free |
| **Tier 2** | Fireworks mid (e.g. **Gemma**) | structured coding, test generation | low |
| **Tier 3** | Fireworks large | deep reasoning, multi-file refactors, subtle debugging | high |

See [docs/architecture.md](docs/architecture.md) for the full design and
[docs/routing.md](docs/routing.md) for the routing/escalation mechanics.

---

## System at a glance

```
Goal in  ──▶  Orchestrator (small model, constrained JSON decode)
                 │  classify → decompose → emit capability_required per step
                 ▼
             Model Registry ── resolves capability → cheapest capable endpoint
                 │   Tier 1: local (AMD GPU pod)   free: classify, extract, simple edits
                 │   Tier 2: Fireworks mid (Gemma)  structured coding, tests
                 │   Tier 3: Fireworks large        deep reasoning, refactor, hard debug
                 ▼
             Tool layer (MCP) ── code-sandbox · git · filesystem · web
                 │   every external result tagged UNTRUSTED
                 ▼
             Execute → run tests → read failures → loop / escalate
                 │   each result carries {confidence, escalation_reason}
                 ▼
             Security plane on every hop:
               egress redaction · untrusted-ingress tagging · confirmation gates
```

---

## Quickstart

> Requires an `FIREWORKS_API_KEY` for Tier 2/3. Tier 1 runs against a local
> OpenAI-compatible endpoint on the AMD GPU pod. TRIARC ships as a single container.

```bash
# 1. clone + configure
git clone https://github.com/<you>/triarc.git && cd triarc
cp .env.example .env            # add FIREWORKS_API_KEY; set local endpoint URL

# 2. run (containerized — the whole app, not just the sandbox)
docker compose up --build

# 3. give it a goal
triarc run "add JWT auth to this Flask app and write tests"
```

Backends: any OpenAI-compatible endpoint registered in `configs/models.yaml`
(local model on AMD hardware for Tier 1; Fireworks AI for Tiers 2–3).

---

## Repository layout

```
triarc/
├── README.md                  # this file
├── docs/
│   ├── architecture.md        # system design (source of truth)
│   ├── routing.md             # routing + escalation mechanics
│   ├── features.md            # feature catalogue (what TRIARC does)
│   ├── security.md            # three-faced security plane
│   ├── amd-fireworks.md       # AMD + Fireworks deployment notes
│   └── roadmap.md             # build phases in dependency order
├── orchestrator/              # registry, router loop, MCP client, task schema
│   ├── servers/                # first-party MCP servers (code-sandbox, git, web)
│   └── api/                    # management API: REST + WebSocket (Phase 4)
├── ui/
│   ├── web/                    # React + TypeScript management dashboard (Phase 4)
│   └── tui/                    # Python Textual management dashboard (Phase 4)
├── configs/                   # model registry, MCP servers, policies (YAML)
└── docker/                    # container definitions
```

---

## Design principles (do not violate)

1. **Small model routes; big models reason.** The orchestrator classifies, decomposes,
   and picks the cheapest capable endpoint. It never does open-ended synthesis.
2. **Everything pluggable through two standards.** Models are OpenAI-compatible
   endpoints in a capability registry; tools are MCP servers. Adding or upgrading a
   model is a config change, zero code change.
3. **Structured output is enforced, not hoped for.** All routing and tool decisions use
   schema-constrained decoding. Model wobble must not break the pipeline.
4. **Fail upward, never bluff.** Every task result carries `confidence` and an
   `escalation_reason`.
5. **Security is three-faced.** Egress (redact secrets before any cloud call), ingress
   (all external content tagged untrusted), and confirmation gates on every irreversible
   action — for every actor, every time.

---

## Why it's a startup, not a demo

Every commercial coding-agent user has the same two complaints: *it costs too much* and
*it does dumb things confidently.* TRIARC's routing layer is a direct, measurable answer
to the first; its confidence-gated escalation is a direct answer to the second. The
routing intelligence is the moat, wrapped into a real autonomous-developer product.

---

## License

MIT. See [LICENSE](LICENSE).

> **Note:** Verify all hackathon prize amounts, track names, and submission requirements
> against the official [lablab.ai event page](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii)
> before submitting.
