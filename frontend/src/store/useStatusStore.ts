import { create } from 'zustand'

type ConnectionStatus = 'connected' | 'disconnected' | 'connecting'
type RobotStatus = 'idle' | 'working' | 'error'

interface StatusState {
  connectionStatus: ConnectionStatus
  robotStatus: RobotStatus
  activeSkills: number
  fps: number
  setConnectionStatus: (status: ConnectionStatus) => void
  setRobotStatus: (status: RobotStatus) => void
  setActiveSkills: (count: number) => void
  setFps: (fps: number) => void
}

export const useStatusStore = create<StatusState>((set) => ({
  connectionStatus: 'disconnected',
  robotStatus: 'idle',
  activeSkills: 0,
  fps: 0,
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  setRobotStatus: (status) => set({ robotStatus: status }),
  setActiveSkills: (count) => set({ activeSkills: count }),
  setFps: (fps) => set({ fps }),
}))
