import { useEffect, useState } from "react";
import type { Scenario } from "../types";

interface Props {
  onExecute: (task: string, state: Record<string, number>) => void;
  isExecuting: boolean;
}

export function TaskPanel({ onExecute, isExecuting }: Props) {
  const [task, setTask] = useState("");
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/agent/scenarios")
      .then((r) => r.json())
      .then((data) => setScenarios(data))
      .catch((e) => console.error("failed to load scenarios", e));
  }, []);

  const handleScenarioClick = (sc: Scenario) => {
    setSelected(sc.name);
    setTask(sc.task);
  };

  const handleExecute = () => {
    if (!task.trim()) return;
    const defaultState = { gripper_open: 1.0 };
    onExecute(task, defaultState);
  };

  const handleReset = () => {
    setTask("");
    setSelected(null);
  };

  return (
    <div className="panel">
      <h2>Task Input</h2>

      <label className="field-label">Task Description</label>
      <textarea
        className="task-input"
        rows={3}
        value={task}
        onChange={(e) => setTask(e.target.value)}
        placeholder="e.g., Pick up the red cube"
        disabled={isExecuting}
      />

      <label className="field-label">Preset Scenarios</label>
      <div className="scenario-list">
        {scenarios.length === 0 && (
          <div className="muted">Loading scenarios...</div>
        )}
        {scenarios.map((sc) => (
          <button
            key={sc.name}
            type="button"
            className={`scenario-btn ${selected === sc.name ? "selected" : ""}`}
            onClick={() => handleScenarioClick(sc)}
            disabled={isExecuting}
            title={sc.description}
          >
            <div className="scenario-name">{sc.name}</div>
            <div className="scenario-desc">{sc.description}</div>
          </button>
        ))}
      </div>

      <div className="button-row">
        <button
          className="btn btn-primary"
          onClick={handleExecute}
          disabled={isExecuting || !task.trim()}
        >
          {isExecuting ? "Executing..." : "Execute"}
        </button>
        <button
          className="btn btn-secondary"
          onClick={handleReset}
          disabled={isExecuting}
        >
          Reset
        </button>
      </div>
    </div>
  );
}
