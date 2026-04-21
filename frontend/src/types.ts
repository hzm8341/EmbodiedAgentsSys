export interface AgentMessage {
  type:
    | 'task_start'
    | 'planning'
    | 'reasoning'
    | 'execution'
    | 'learning'
    | 'result'
    | 'error'
  timestamp?: number
  status?: string
  data?: Record<string, unknown>
}

export interface Scenario {
  name: string
  description: string
  task: string
}

export interface ExecuteTaskRequest {
  type: 'execute_task'
  task: string
  scenario?: string
  observation: { state: Record<string, number> }
  max_steps?: number
}
