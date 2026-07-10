import { useEffect, useState } from "react";
import { api } from "../api";
import type { GateOut, RedactionLogEntry } from "../types";

const POLL_MS = 2000;

export function GatesView() {
  const [gates, setGates] = useState<GateOut[]>([]);
  const [redactionLog, setRedactionLog] = useState<RedactionLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () => {
      api.listGates().then(setGates).catch((err) => setError(String(err)));
      api.getRedactionLog().then(setRedactionLog).catch((err) => setError(String(err)));
    };
    refresh();
    const interval = setInterval(refresh, POLL_MS);
    return () => clearInterval(interval);
  }, []);

  async function resolve(gateId: string, approved: boolean) {
    try {
      await api.resolveGate(gateId, approved);
      const gates = await api.listGates();
      setGates(gates);
    } catch (err) {
      setError(String(err));
    }
  }

  const pending = gates.filter((gate) => gate.decision === "pending");
  const resolved = gates.filter((gate) => gate.decision !== "pending");

  return (
    <div className="view">
      <h2>Confirmation gate inbox</h2>
      {error && <p className="error">{error}</p>}

      <h3>Pending</h3>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Detail</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {pending.map((gate) => (
            <tr key={gate.gate_id}>
              <td>{gate.action}</td>
              <td>{gate.detail}</td>
              <td>
                <button onClick={() => resolve(gate.gate_id, true)}>Approve</button>
                <button onClick={() => resolve(gate.gate_id, false)}>Deny</button>
              </td>
            </tr>
          ))}
          {pending.length === 0 && (
            <tr>
              <td colSpan={3} className="empty">
                No pending gates -- irreversible actions are gated automatically when they occur.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <h3>History</h3>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Detail</th>
            <th>Decision</th>
          </tr>
        </thead>
        <tbody>
          {resolved.map((gate) => (
            <tr key={gate.gate_id}>
              <td>{gate.action}</td>
              <td>{gate.detail}</td>
              <td>{gate.decision}</td>
            </tr>
          ))}
          {resolved.length === 0 && (
            <tr>
              <td colSpan={3} className="empty">
                No resolved gates yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <h3>Egress redaction log</h3>
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Kind</th>
            <th>Matched</th>
          </tr>
        </thead>
        <tbody>
          {redactionLog.map((entry, index) => (
            <tr key={index}>
              <td>{entry.timestamp}</td>
              <td>{entry.kind}</td>
              <td>{entry.matched}</td>
            </tr>
          ))}
          {redactionLog.length === 0 && (
            <tr>
              <td colSpan={3} className="empty">
                Nothing redacted yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
