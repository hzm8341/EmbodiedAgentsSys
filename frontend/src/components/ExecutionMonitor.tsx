import type { AgentMessage } from "../types";

interface Props {
  messages: AgentMessage[];
  isExecuting: boolean;
}

function findLast(messages: AgentMessage[], type: AgentMessage["type"]) {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].type === type) return messages[i];
  }
  return null;
}

function countByType(messages: AgentMessage[], type: AgentMessage["type"]) {
  return messages.filter((m) => m.type === type).length;
}

function LayerCard({
  title,
  message,
  active,
  accentClass,
  count,
}: {
  title: string;
  message: AgentMessage | null;
  active: boolean;
  accentClass: string;
  count?: number;
}) {
  return (
    <div className={`layer-card ${active ? `active ${accentClass}` : ""}`}>
      <div className="layer-header">
        <span className="layer-title">{title}</span>
        {count !== undefined && count > 0 && (
          <span className="layer-count">×{count}</span>
        )}
      </div>
      {message ? (
        <pre className="layer-body">
          {JSON.stringify(message.data, null, 2)}
        </pre>
      ) : (
        <div className="layer-placeholder">Waiting...</div>
      )}
    </div>
  );
}

export function ExecutionMonitor({ messages, isExecuting }: Props) {
  const planning = findLast(messages, "planning");
  const reasoning = findLast(messages, "reasoning");
  const learning = findLast(messages, "learning");
  const execution = findLast(messages, "execution");

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Execution Monitor</h2>
        {isExecuting && <span className="badge running">Running</span>}
      </div>
      <div className="layer-grid">
        <LayerCard
          title="Planning Layer"
          message={planning}
          active={!!planning}
          accentClass="accent-planning"
        />
        <LayerCard
          title="Reasoning Layer"
          message={reasoning}
          active={!!reasoning}
          accentClass="accent-reasoning"
          count={countByType(messages, "reasoning")}
        />
        <LayerCard
          title="Execution"
          message={execution}
          active={!!execution}
          accentClass="accent-execution"
          count={countByType(messages, "execution")}
        />
        <LayerCard
          title="Learning Layer"
          message={learning}
          active={!!learning}
          accentClass="accent-learning"
          count={countByType(messages, "learning")}
        />
      </div>
    </div>
  );
}
