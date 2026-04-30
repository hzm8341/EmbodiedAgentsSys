export interface AgentMessage {
  protocol_version?: string
  type:
    | 'task_start'
    | 'planning'
    | 'reasoning'
    | 'execution'
    | 'learning'
    | 'result'
    | 'error'
  trace_id?: string
  step?: number
  timestamp?: number
  status?: string
  error_code?: string | null
  payload?: Record<string, unknown>
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
