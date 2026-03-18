import { useState } from 'react'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { MainArea } from './components/MainArea'

function App() {
  const [activeItem, setActiveItem] = useState('chat')

  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar activeItem={activeItem} onItemSelected={setActiveItem} />
        <MainArea activeItem={activeItem} />
      </div>
    </div>
  )
}

export default App
