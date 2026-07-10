export type RunStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface Task {
  task_id: string;
  goal: string;
  capability_required: string;
  context_refs: string[];
  constraints: { privacy: string; max_cost: number | null };
  result: string | null;
  confidence: number;
  escalation_reason: string | null;
}

export interface RoutedStepOut {
  endpoint_id: string;
  task: Task;
}

export interface StepOutcomeOut {
  task_id: string;
  attempts: number;
  passed: boolean;
  escalations: string[];
}

export interface StepLogOut {
  task_id: string;
  goal: string;
  tier: number | null;
  endpoint_id: string;
  tokens: number;
  cost: number;
  confidence: number;
  escalated: boolean;
  passed: boolean | null;
}

export interface CostSummaryOut {
  step_count: number;
  escalated_count: number;
  actual_cost: number;
  baseline_cost: number;
  savings: number;
}

export interface RunOut {
  run_id: string;
  goal: string;
  status: RunStatus;
  routed_steps: RoutedStepOut[];
  outcomes: StepOutcomeOut[];
  telemetry: StepLogOut[];
  cost_summary: CostSummaryOut | null;
  error: string | null;
}

export interface RunSummaryOut {
  run_id: string;
  goal: string;
  status: RunStatus;
}

export interface ModelEndpoint {
  id: string;
  endpoint: string;
  model: string | null;
  capabilities: string[];
  cost: number;
  privacy: string;
  tier: number | null;
}

export interface GateOut {
  gate_id: string;
  action: string;
  detail: string;
  decision: "pending" | "approved" | "denied";
}

export interface RedactionLogEntry {
  timestamp: string;
  kind: string;
  matched: string;
}
