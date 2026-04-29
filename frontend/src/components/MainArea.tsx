import type { SidebarItem } from './Sidebar'
import { AgentWorkspace } from './AgentWorkspace'
import { ChatPanel }      from './ChatPanel'
import { CameraPanel }    from './CameraPanel'
import { DetectionPanel } from './DetectionPanel'
import { SettingsPanel }  from './SettingsPanel'
import { URDFPanel }      from './URDFPanel'

interface Props {
  active: SidebarItem
}

export const MainArea = ({ active }: Props) => (
  <main className="flex-1 bg-gray-100 p-5 overflow-auto min-w-0">
    {active === 'agent'     && <AgentWorkspace />}
    {active === 'urdf'      && <URDFPanel />}
    {active === 'chat'      && <ChatPanel />}
    {active === 'camera'    && <CameraPanel />}
    {active === 'detection' && <DetectionPanel />}
    {active === 'settings'  && <SettingsPanel />}
  </main>
)
