import { ChatPanel } from './ChatPanel'
import { CameraPanel } from './CameraPanel'
import { DetectionPanel } from './DetectionPanel'
import { ScenePanel } from './ScenePanel'
import { SettingsPanel } from './SettingsPanel'

interface MainAreaProps {
  activeItem: string
}

export const MainArea = ({ activeItem }: MainAreaProps) => {
  return (
    <main className="flex-1 bg-gray-100 dark:bg-gray-900 p-6 overflow-auto">
      {activeItem === 'chat' && <ChatPanel />}
      {activeItem === 'camera' && <CameraPanel />}
      {activeItem === 'scene' && <ScenePanel />}
      {activeItem === 'detection' && <DetectionPanel />}
      {activeItem === 'settings' && <SettingsPanel />}
    </main>
  )
}
