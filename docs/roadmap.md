# Roadmap — hackathon build phases

Rule: each phase ships something demoable. Build in dependency order; don't scaffold
later phases beyond stub interfaces.

## Phase 0 — Skeleton (½ day)
**Deliverable:** the container comes up and echoes a routed plan.
- [ ] `orchestrator/schema.py` — the task schema (pydantic)
- [ ] `orchestrator/registry.py` — model registry loading `configs/models.yaml`
- [ ] Constrained-decoding client against Tier 1 (local endpoint)
- [ ] `docker compose up` brings up the app

## Phase 1 — Route + execute (core loop)  ⟵ THE PRODUCT
**Deliverable:** a real goal produces working code.
- [ ] Router/planner loop: goal → plan → per-step capability emission
- [ ] Registry resolution (Tier 1 → 2 → 3) with the routing algorithm
- [ ] `orchestrator/servers/code-sandbox/` — containerized execution
- [ ] `git` + `filesystem` MCP servers (workspace-scoped)
- [ ] Test-run-read-fix loop

## Phase 2 — Escalation + gates
**Deliverable:** fail-upward works; irreversible actions are gated.
- [ ] `confidence` + `escalation_reason` handling; reactive escalation ladder
- [ ] Egress gatekeeper (secret/PII redaction before Tier 3)
- [ ] Untrusted-ingress tagging for tool/web content
- [ ] Confirmation-gate framework

## Phase 3 — Telemetry + cost demo  ⟵ THE MONEY-SHOT
**Deliverable:** the run summary that wins Track 3.
- [ ] Per-step logging: tier, endpoint, tokens, cost, confidence, escalated
- [ ] Run summary: actual vs all-frontier-baseline cost + savings
- [ ] A simple visual (terminal table or small web view) for the demo video

## Phase 4 — Packaging & submission
- [ ] Whole-app container verified runnable from README instructions
- [ ] `web` MCP server for lookups (optional but nice)
- [ ] README + docs finalized; MIT LICENSE added
- [ ] Cover image (routing diagram), demo video, slides
- [ ] Gemma confirmed as the Tier-2 model (Gemma prize)

## Cut lines (if time runs short)
Drop in this order: `web` server → visual polish on the cost view → predictive
escalation (keep reactive). **Never cut:** the core loop, the security gates, and the
cost telemetry — those are the three things the submission is judged on.
