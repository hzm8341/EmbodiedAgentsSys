import { create } from 'zustand'

type ConnectionStatus = 'connected' | 'disconnected' | 'connecting'
type RobotStatus = 'idle' | 'working' | 'error'

interface StatusState {
  connectionStatus: ConnectionStatus
  robotStatus: RobotStatus
  selectedBackend: string
  sceneConnected: boolean
  activeSkills: number
  fps: number
  setConnectionStatus: (status: ConnectionStatus) => void
  setRobotStatus: (status: RobotStatus) => void
  setSelectedBackend: (backend: string) => void
  setSceneConnected: (connected: boolean) => void
  setActiveSkills: (count: number) => void
  setFps: (fps: number) => void
}

export const useStatusStore = create<StatusState>((set) => ({
  connectionStatus: 'disconnected',
  robotStatus: 'idle',
  selectedBackend: 'mujoco',
  sceneConnected: false,
  activeSkills: 0,
  fps: 0,
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  setRobotStatus: (status) => set({ robotStatus: status }),
  setSelectedBackend: (backend) => set({ selectedBackend: backend }),
  setSceneConnected: (connected) => set({ sceneConnected: connected }),
  setActiveSkills: (count) => set({ activeSkills: count }),
  setFps: (fps) => set({ fps }),
}))
