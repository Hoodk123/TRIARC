import { useState } from "react";
import "./App.css";
import { GatesView } from "./views/GatesView";
import { RegistryView } from "./views/RegistryView";
import { RunsView } from "./views/RunsView";

type Tab = "runs" | "registry" | "gates";

const TABS: { id: Tab; label: string }[] = [
  { id: "runs", label: "Runs" },
  { id: "registry", label: "Model registry" },
  { id: "gates", label: "Confirmation gates" },
];

function App() {
  const [tab, setTab] = useState<Tab>("runs");

  return (
    <div className="app">
      <header>
        <h1>TRIARC</h1>
        <nav>
          {TABS.map(({ id, label }) => (
            <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === "runs" && <RunsView />}
        {tab === "registry" && <RegistryView />}
        {tab === "gates" && <GatesView />}
      </main>
    </div>
  );
}

export default App;
