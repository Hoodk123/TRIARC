import { useEffect, useState } from "react";
import { api } from "../api";
import type { ModelEndpoint } from "../types";

export function RegistryView() {
  const [entries, setEntries] = useState<ModelEndpoint[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftCost, setDraftCost] = useState("");
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.getRegistry().then(setEntries).catch((err) => setError(String(err)));
  }

  useEffect(refresh, []);

  function startEdit(entry: ModelEndpoint) {
    setEditingId(entry.id);
    setDraftCost(String(entry.cost));
  }

  async function saveEdit(id: string) {
    const cost = Number(draftCost);
    if (Number.isNaN(cost)) {
      setError(`"${draftCost}" is not a number`);
      return;
    }
    try {
      await api.updateRegistryEntry(id, { cost });
      setEditingId(null);
      refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div className="view">
      <h2>Model registry</h2>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Tier</th>
            <th>Endpoint</th>
            <th>Capabilities</th>
            <th>Cost</th>
            <th>Privacy</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td>{entry.id}</td>
              <td>{entry.tier ?? "-"}</td>
              <td>{entry.endpoint}</td>
              <td>{entry.capabilities.join(", ")}</td>
              <td>
                {editingId === entry.id ? (
                  <input
                    value={draftCost}
                    onChange={(event) => setDraftCost(event.target.value)}
                    className="cost-input"
                  />
                ) : (
                  entry.cost.toFixed(2)
                )}
              </td>
              <td>{entry.privacy}</td>
              <td>
                {editingId === entry.id ? (
                  <>
                    <button onClick={() => saveEdit(entry.id)}>Save</button>
                    <button onClick={() => setEditingId(null)}>Cancel</button>
                  </>
                ) : (
                  <button onClick={() => startEdit(entry)}>Edit</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
