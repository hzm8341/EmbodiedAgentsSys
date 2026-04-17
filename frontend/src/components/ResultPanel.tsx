import { useState } from "react";
import type { AgentMessage } from "../types";

interface Props {
  messages: AgentMessage[];
}

export function ResultPanel({ messages }: Props) {
  const [showLog, setShowLog] = useState(false);
  const result = messages.find((m) => m.type === "result");
  const errors = messages.filter((m) => m.type === "error");
  const hasResult = !!result;
  const success =
    (result?.data?.task_success as boolean | undefined) ?? false;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Execution Results</h2>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => setShowLog((v) => !v)}
        >
          {showLog ? "Hide Log" : "Show Log"}
        </button>
      </div>

      {!hasResult ? (
        <div className="muted">Execute a task to see results.</div>
      ) : (
        <>
          <div className={`status-pill ${success ? "ok" : "fail"}`}>
            {success ? "✓ Task Success" : "✗ Task Failed"}
          </div>
          <pre className="result-body">
            {JSON.stringify(result?.data, null, 2)}
          </pre>
        </>
      )}

      {errors.length > 0 && (
        <div className="error-box">
          <div className="error-title">Errors:</div>
          {errors.map((e, i) => (
            <div key={i}>{(e.data as { message?: string })?.message}</div>
          ))}
        </div>
      )}

      {showLog && (
        <div className="log-box">
          {messages.map((m, i) => (
            <div key={i} className="log-line">
              <span className="log-type">[{m.type}]</span>{" "}
              {m.timestamp ? new Date(m.timestamp * 1000).toLocaleTimeString() : ""}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
