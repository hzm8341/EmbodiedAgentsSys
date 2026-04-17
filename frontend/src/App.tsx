import { useEffect, useState } from "react";
import { TaskPanel } from "./components/TaskPanel";
import { ExecutionMonitor } from "./components/ExecutionMonitor";
import { ObservationPanel } from "./components/ObservationPanel";
import { ResultPanel } from "./components/ResultPanel";
import { useAgentWebSocket } from "./hooks/useAgentWebSocket";

function App() {
  const { isConnected, messages, executeTask, clearMessages } =
    useAgentWebSocket();
  const [isExecuting, setIsExecuting] = useState(false);

  useEffect(() => {
    if (messages.some((m) => m.type === "result")) {
      setIsExecuting(false);
    }
  }, [messages]);

  const handleExecute = (task: string, state: Record<string, number>, scenario?: string) => {
    clearMessages();
    setIsExecuting(true);
    executeTask(task, state, scenario, 3);
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <h1>Embodied Agents — Interactive Debugger</h1>
        <span
          className={`connection-badge ${
            isConnected ? "connected" : "disconnected"
          }`}
        >
          {isConnected ? "● Connected" : "● Disconnected"}
        </span>
      </header>

      <div className="app-grid">
        <div className="col-left">
          <TaskPanel onExecute={handleExecute} isExecuting={isExecuting} />
          <ObservationPanel messages={messages} />
        </div>
        <div className="col-right">
          <ExecutionMonitor messages={messages} isExecuting={isExecuting} />
          <ResultPanel messages={messages} />
        </div>
      </div>
    </div>
  );
}

export default App;
