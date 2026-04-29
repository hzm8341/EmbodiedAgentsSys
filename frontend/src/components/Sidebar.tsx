export type SidebarItem = 'agent' | 'urdf' | 'chat' | 'camera' | 'detection' | 'settings'

const ITEMS: { id: SidebarItem; icon: string; label: string }[] = [
  { id: 'agent',     icon: '🤖', label: 'Agent 调试器' },
  { id: 'urdf',      icon: '🦾', label: 'URDF 视图' },
  { id: 'chat',      icon: '💬', label: '聊天控制' },
  { id: 'camera',    icon: '📷', label: '相机' },
  { id: 'detection', icon: '🎯', label: '目标检测' },
  { id: 'settings',  icon: '⚙️', label: '设置' },
]

interface Props {
  active: SidebarItem
  onSelect: (id: SidebarItem) => void
}

export const Sidebar = ({ active, onSelect }: Props) => (
  <aside className="w-48 bg-gray-900 text-white flex flex-col shrink-0">
    <nav className="flex-1 py-4">
      {ITEMS.map((item) => (
        <button
          key={item.id}
          onClick={() => onSelect(item.id)}
          className={`w-full px-4 py-3 text-left text-sm flex items-center gap-3 transition-colors
            hover:bg-gray-700
            ${active === item.id ? 'bg-gray-700 border-l-2 border-blue-400' : ''}`}
        >
          <span className="text-base">{item.icon}</span>
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  </aside>
)
