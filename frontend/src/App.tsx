import { useState } from 'react'
import { Header } from './components/Header'
import { Sidebar, type SidebarItem } from './components/Sidebar'
import { MainArea } from './components/MainArea'

function App() {
  const [active, setActive] = useState<SidebarItem>('agent')

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={active} onSelect={setActive} />
        <MainArea active={active} />
      </div>
    </div>
  )
}

export default App
