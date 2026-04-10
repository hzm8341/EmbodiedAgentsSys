type SidebarItem = {
  id: string
  icon: string
  label: string
}

const items: SidebarItem[] = [
  { id: 'chat', icon: '📝', label: '对话' },
  { id: 'camera', icon: '📷', label: '相机' },
  { id: 'scene', icon: '🔍', label: '场景分析' },
  { id: 'detection', icon: '🎯', label: '检测' },
  { id: 'robot', icon: '🤖', label: '机器人控制' },
  { id: 'settings', icon: '⚙️', label: '设置' },
]

interface SidebarProps {
  activeItem: string
  onItemSelected: (id: string) => void
}

export const Sidebar = ({ activeItem, onItemSelected }: SidebarProps) => {
  return (
    <aside className="w-60 bg-gray-900 text-white flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Embodied Agents</h2>
      </div>
      <nav className="flex-1 py-4">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => onItemSelected(item.id)}
            className={`w-full px-4 py-3 text-left flex items-center gap-3 hover:bg-gray-800 ${
              activeItem === item.id ? 'bg-gray-700' : ''
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  )
}
