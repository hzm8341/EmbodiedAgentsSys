export interface AgentMessage {
  type:
    | "task_start"
    | "planning"
    | "reasoning"
    | "execution"
    | "learning"
    | "result"
    | "error";
  timestamp?: number;
  status?: string;
  data?: Record<string, unknown>;
}

export interface Scenario {
  name: string;
  description: string;
  task: string;
}

export interface ObservationState {
  [key: string]: number;
}

export interface ExecuteTaskRequest {
  type: "execute_task";
  task: string;
  observation: {
    state: ObservationState;
    gripper?: ObservationState;
  };
  max_steps?: number;
}
