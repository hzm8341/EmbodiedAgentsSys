import type { SidebarItem } from './Sidebar'
import { AgentPanel }     from './AgentPanel'
import { ChatPanel }      from './ChatPanel'
import { CameraPanel }    from './CameraPanel'
import { DetectionPanel } from './DetectionPanel'
import { SettingsPanel }  from './SettingsPanel'

interface Props {
  active: SidebarItem
}

export const MainArea = ({ active }: Props) => (
  <main className="flex-1 bg-gray-100 p-5 overflow-auto min-w-0">
    {active === 'agent'     && <AgentPanel />}
    {active === 'chat'      && <ChatPanel />}
    {active === 'camera'    && <CameraPanel />}
    {active === 'detection' && <DetectionPanel />}
    {active === 'settings'  && <SettingsPanel />}
  </main>
)
