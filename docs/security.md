# Security Plane

The security plane has **three faces**. All three are mandatory; none is UX polish. An
agent that can execute code and reach the network must be treated as a security surface,
regardless of how capable the underlying model is.

## Face 1 — Egress: the gatekeeper (data leaving the machine)

- Runs locally, before ANY payload reaches a Tier-3 (cloud) endpoint.
- Strips/redacts: API keys and secrets (entropy + pattern detection), file paths and
  usernames, emails/phone numbers, and configured custom patterns (project names, etc.).
- Tier-3 calls require BOTH: the task's `constraints.privacy == cloud_ok` AND a
  gatekeeper pass.
- A redaction log is kept locally so you can audit exactly what left the machine.

## Face 2 — Ingress: untrusted content (data entering the model)

- ALL external content — web pages, MCP tool results, file contents — is wrapped in
  tagged untrusted-data blocks before entering any model context. It is data to
  transform, never instructions to follow.
- **No chaining from untrusted content to irreversible action:** a model turn whose
  context contains untrusted content cannot trigger code exec outside the sandbox, file
  deletion, or outbound messaging without a confirmation gate — regardless of anything
  the content says.
- Web/tool access is allowlist/session-scoped so a hijacked model cannot wander.

## Face 3 — Confirmation gates (irreversible actions)

Always gated, from every entry point:

- code execution **outside** the sandbox
- file deletion / destructive file ops
- sending messages / posting content outward
- purchases or anything spending money

Gates are non-negotiable and apply even when the user initiated the run — accounts get
compromised and content gets injected. A gate surfaces the exact action and waits for
explicit confirmation before proceeding.

## Code sandbox

- All model-initiated code runs in containers: rootless, no network by default,
  workspace-scoped mounts, resource limits, timeout.
- Network access inside the sandbox is per-task opt-in and allowlisted.
- Sandbox-escape attempts and denied syscalls are logged and surfaced.

## Review invariants

- [ ] Every payload to a Tier-3 endpoint passes the egress gatekeeper.
- [ ] Every external content path is wrapped in untrusted tags.
- [ ] Every irreversible action path hits a confirmation gate.
- [ ] No tool exposed to any model can modify security policy or gate behavior.
- [ ] The Tier-3 path checks task consent (`privacy: cloud_ok`) AND gatekeeper pass.
