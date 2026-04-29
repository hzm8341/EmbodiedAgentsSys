import { create } from 'zustand'

export interface SyncStep {
  step: number
  action: string
  arm?: string
  target?: [number, number, number]
  actual?: [number, number, number]
  success?: boolean
  error?: number
  timestamp: number
}

interface SyncState {
  currentTask: string
  activeStep: number
  activeAction: string
  activeArm: string
  target: [number, number, number] | null
  actual: [number, number, number] | null
  error: number | null
  history: SyncStep[]
  setCurrentTask: (task: string) => void
  setReasoningAction: (step: number, action: string, arm: string, target: [number, number, number] | null) => void
  commitExecution: (payload: {
    step: number
    action: string
    arm?: string
    target?: [number, number, number]
    actual?: [number, number, number]
    success?: boolean
    timestamp: number
  }) => void
  clearSync: () => void
}

export const useSyncStore = create<SyncState>((set) => ({
  currentTask: '',
  activeStep: -1,
  activeAction: '',
  activeArm: '',
  target: null,
  actual: null,
  error: null,
  history: [],
  setCurrentTask: (task) => set({ currentTask: task }),
  setReasoningAction: (step, action, arm, target) =>
    set({
      activeStep: step,
      activeAction: action,
      activeArm: arm,
      target,
      actual: null,
      error: null,
    }),
  commitExecution: ({ step, action, arm, target, actual, success, timestamp }) =>
    set((state) => {
      let error: number | null = null
      if (target && actual) {
        const dx = target[0] - actual[0]
        const dy = target[1] - actual[1]
        const dz = target[2] - actual[2]
        error = Math.sqrt(dx * dx + dy * dy + dz * dz)
      }
      return {
        activeStep: step,
        activeAction: action,
        activeArm: arm ?? state.activeArm,
        target: target ?? state.target,
        actual: actual ?? state.actual,
        error,
        history: [
          ...state.history,
          { step, action, arm, target, actual, success, error: error ?? undefined, timestamp },
        ].slice(-30),
      }
    }),
  clearSync: () =>
    set({
      currentTask: '',
      activeStep: -1,
      activeAction: '',
      activeArm: '',
      target: null,
      actual: null,
      error: null,
      history: [],
    }),
}))
