import type { AgentMessage } from "../types";

interface Props {
  messages: AgentMessage[];
}

export function ObservationPanel({ messages }: Props) {
  const taskStart = messages.find((m) => m.type === "task_start");
  const currentTask = (taskStart?.data?.task as string) ?? "(none)";

  return (
    <div className="panel">
      <h2>Robot Observation</h2>
      <div className="field">
        <span className="field-key">Current Task:</span>
        <span className="field-value">{currentTask}</span>
      </div>
      <div className="field">
        <span className="field-key">Messages:</span>
        <span className="field-value">{messages.length}</span>
      </div>
      <div className="field">
        <span className="field-key">Layers seen:</span>
        <span className="field-value">
          {Array.from(new Set(messages.map((m) => m.type))).join(", ") ||
            "(none)"}
        </span>
      </div>
    </div>
  );
}
