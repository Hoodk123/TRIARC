import { useEffect, useRef, useState } from "react";
import { api, wsUrlForRun } from "../api";
import type { RunOut, RunSummaryOut } from "../types";

const LIST_POLL_MS = 2000;

export function RunsView() {
  const [runs, setRuns] = useState<RunSummaryOut[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunOut | null>(null);
  const [goal, setGoal] = useState("");
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const refresh = () => api.listRuns().then(setRuns).catch((err) => setError(String(err)));
    refresh();
    const interval = setInterval(refresh, LIST_POLL_MS);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    socketRef.current?.close();
    setSelectedRun(null);
    if (!selectedRunId) return;

    const socket = new WebSocket(wsUrlForRun(selectedRunId));
    socket.onmessage = (event) => setSelectedRun(JSON.parse(event.data) as RunOut);
    socket.onerror = () => setError(`websocket error for run ${selectedRunId}`);
    socketRef.current = socket;
    return () => socket.close();
  }, [selectedRunId]);

  async function handleStartRun(event: React.FormEvent) {
    event.preventDefault();
    if (!goal.trim()) return;
    try {
      const started = await api.startRun(goal.trim());
      setGoal("");
      setRuns((prev) => [started, ...prev]);
      setSelectedRunId(started.run_id);
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleCancel() {
    if (!selectedRunId) return;
    try {
      await api.cancelRun(selectedRunId);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div className="view">
      {error && <p className="error">{error}</p>}

      <section>
        <h2>Run monitoring &amp; control</h2>
        <form onSubmit={handleStartRun} className="start-run-form">
          <input
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            placeholder="add JWT auth to this Flask app and write tests"
          />
          <button type="submit">Start run</button>
        </form>

        <ul className="run-list">
          {runs.map((run) => (
            <li
              key={run.run_id}
              className={run.run_id === selectedRunId ? "selected" : ""}
              onClick={() => setSelectedRunId(run.run_id)}
            >
              <span className={`status-badge status-${run.status}`}>{run.status}</span>
              {run.goal}
            </li>
          ))}
          {runs.length === 0 && <li className="empty">No runs yet.</li>}
        </ul>

        {selectedRun && (
          <div className="run-detail">
            <div className="run-detail-header">
              <strong>{selectedRun.goal}</strong>
              <span className={`status-badge status-${selectedRun.status}`}>{selectedRun.status}</span>
              {(selectedRun.status === "pending" || selectedRun.status === "running") && (
                <button onClick={handleCancel}>Cancel</button>
              )}
            </div>
            {selectedRun.error && <p className="error">{selectedRun.error}</p>}

            <table>
              <thead>
                <tr>
                  <th>Step</th>
                  <th>Endpoint</th>
                  <th>Attempts</th>
                  <th>Passed</th>
                  <th>Escalations</th>
                </tr>
              </thead>
              <tbody>
                {selectedRun.routed_steps.map((step) => {
                  const outcome = selectedRun.outcomes.find((o) => o.task_id === step.task.task_id);
                  return (
                    <tr key={step.task.task_id}>
                      <td>{step.task.goal}</td>
                      <td>{step.endpoint_id}</td>
                      <td>{outcome?.attempts ?? "-"}</td>
                      <td>{outcome ? (outcome.passed ? "yes" : "no") : "-"}</td>
                      <td>{outcome?.escalations.join("; ") || "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selectedRun && (
        <section>
          <h2>Cost &amp; routing telemetry</h2>
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Tier</th>
                <th>Endpoint</th>
                <th>Tokens</th>
                <th>Cost</th>
                <th>Confidence</th>
                <th>Escalated</th>
                <th>Passed</th>
              </tr>
            </thead>
            <tbody>
              {selectedRun.telemetry.map((log, index) => (
                <tr key={index}>
                  <td>{log.goal}</td>
                  <td>{log.tier ?? "-"}</td>
                  <td>{log.endpoint_id}</td>
                  <td>{log.tokens}</td>
                  <td>{log.cost.toFixed(2)}</td>
                  <td>{log.confidence.toFixed(2)}</td>
                  <td>{log.escalated ? "yes" : "no"}</td>
                  <td>{log.passed === null ? "-" : log.passed ? "yes" : "no"}</td>
                </tr>
              ))}
              {selectedRun.telemetry.length === 0 && (
                <tr>
                  <td colSpan={8} className="empty">
                    No steps logged yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {selectedRun.cost_summary && (
            <table className="summary-table">
              <tbody>
                <tr>
                  <td>Steps</td>
                  <td>{selectedRun.cost_summary.step_count}</td>
                </tr>
                <tr>
                  <td>Escalated steps</td>
                  <td>{selectedRun.cost_summary.escalated_count}</td>
                </tr>
                <tr>
                  <td>Actual cost</td>
                  <td>{selectedRun.cost_summary.actual_cost.toFixed(2)}</td>
                </tr>
                <tr>
                  <td>Baseline cost (all-frontier)</td>
                  <td>{selectedRun.cost_summary.baseline_cost.toFixed(2)}</td>
                </tr>
                <tr>
                  <td>
                    <strong>Savings</strong>
                  </td>
                  <td>
                    <strong>{selectedRun.cost_summary.savings.toFixed(2)}</strong>
                  </td>
                </tr>
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
