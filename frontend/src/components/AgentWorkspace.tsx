import { AgentPanel } from './AgentPanel'
import { URDFPanel } from './URDFPanel'

export const AgentWorkspace = () => (
  <div className="h-full grid grid-cols-[minmax(420px,1fr)_minmax(520px,1.2fr)] gap-4 min-w-0">
    <section className="min-w-0 overflow-auto">
      <AgentPanel />
    </section>
    <section className="min-w-0 overflow-auto">
      <URDFPanel embedded />
    </section>
  </div>
)
