import { useEffect, useState } from 'react'
import { useSyncStore } from '../store/useSyncStore'

interface RobotInfo {
  robot_id: string
  name: string
  urdf_path: string
}

interface LinkInfo {
  name: string
  visual_geometry?: string | null
}

interface JointInfo {
  name: string
  type: string
  parent: string
  child: string
}

interface URDFModel {
  name: string
  links: LinkInfo[]
  joints: JointInfo[]
}

const VUER_PORT = 8012
const VUER_CLIENT_URL = import.meta.env.VITE_VUER_CLIENT_URL ?? 'https://vuer.ai'

interface URDFPanelProps {
  embedded?: boolean
}

const ROBOT_STORAGE_KEY = 'eas_selected_robot'

export const URDFPanel = ({ embedded = false }: URDFPanelProps) => {
  const [robots, setRobots] = useState<RobotInfo[]>([])
  const [selectedRobot, setSelectedRobot] = useState(
    () => window.localStorage.getItem(ROBOT_STORAGE_KEY) || 'eyoubot'
  )
  const [model, setModel] = useState<URDFModel | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { currentTask, activeStep, activeAction, activeArm, target, actual, error: syncError, history } = useSyncStore()

  useEffect(() => {
    fetch('/api/urdf/list')
      .then((r) => {
        if (!r.ok) throw new Error('URDF list request failed')
        return r.json()
      })
      .then((items: RobotInfo[]) => {
        setRobots(items)
        if (items.length === 0) return
        const currentValid = items.some((item) => item.robot_id === selectedRobot)
        if (!currentValid) {
          setSelectedRobot(items[0].robot_id)
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load robots'))
  }, [selectedRobot])

  useEffect(() => {
    if (!selectedRobot) return
    fetch(`/api/urdf/${selectedRobot}`)
      .then((r) => {
        if (!r.ok) throw new Error('URDF model request failed')
        return r.json()
      })
      .then(setModel)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load URDF'))
  }, [selectedRobot])

  useEffect(() => {
    if (!selectedRobot) return
    window.localStorage.setItem(ROBOT_STORAGE_KEY, selectedRobot)
    fetch(`/switch_robot?robot=${encodeURIComponent(selectedRobot)}`).catch(() => undefined)
  }, [selectedRobot])

  const iframeUrl = `${VUER_CLIENT_URL}?ws=ws://localhost:${VUER_PORT}&robot=${encodeURIComponent(selectedRobot)}`

  const rootClass = embedded ? 'h-full flex flex-col gap-3' : 'h-full flex flex-col gap-4'

  return (
    <div className={rootClass}>
      <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-gray-800">URDF 视图</h2>
          <p className="text-xs text-gray-500 mt-1">Vuer: ws://localhost:{VUER_PORT}</p>
        </div>
        <select
          value={selectedRobot}
          onChange={(e) => setSelectedRobot(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm bg-white"
        >
          {robots.length === 0 && <option value="eyoubot">eyoubot</option>}
          {robots.map((robot) => (
            <option key={`${robot.robot_id}:${robot.urdf_path}`} value={robot.robot_id}>
              {robot.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className={`flex-1 ${embedded ? 'min-h-[420px]' : 'min-h-[520px]'} grid grid-cols-[minmax(0,1fr)_280px] gap-4`}>
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="relative w-full h-full">
            <iframe
              key={selectedRobot}
              src={iframeUrl}
              className="w-full h-full border-0"
              title="Vuer URDF Viewer"
              allow="xr-spatial-tracking"
            />
            <div className="absolute left-3 top-3 bg-white/95 border border-gray-200 rounded-md px-3 py-2 text-xs text-gray-700 min-w-[260px]">
              <div className="font-semibold text-gray-800 mb-1">同步状态</div>
              <div>Task: <span className="font-medium">{currentTask || '(none)'}</span></div>
              <div>Step: <span className="font-medium">{activeStep >= 0 ? activeStep : '-'}</span></div>
              <div>Action: <span className="font-medium">{activeAction || '-'}</span></div>
              <div>Arm: <span className="font-medium">{activeArm || '-'}</span></div>
              <div>Target: <span className="font-mono">{target ? target.map((v) => v.toFixed(3)).join(', ') : '-'}</span></div>
              <div>Actual: <span className="font-mono">{actual ? actual.map((v) => v.toFixed(3)).join(', ') : '-'}</span></div>
              <div>
                Error:
                <span className={`font-medium ${syncError !== null && syncError > 0.05 ? 'text-red-600' : 'text-green-700'}`}>
                  {' '}{syncError !== null ? `${syncError.toFixed(4)} m` : '-'}
                </span>
              </div>
            </div>
          </div>
        </div>

        <aside className="bg-white border border-gray-200 rounded-lg overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-sm font-bold text-gray-800">模型结构</h3>
            <p className="text-xs text-gray-500 mt-1">
              {model ? `${model.links.length} links / ${model.joints.length} joints` : 'Loading...'}
            </p>
          </div>
          <div className="flex-1 overflow-auto p-3 space-y-3">
            <ModelTree model={model} />
            <div className="pt-2 border-t border-gray-200">
              <p className="text-xs font-semibold text-gray-700 mb-2">动作时间线（最近）</p>
              <div className="space-y-1 max-h-40 overflow-auto">
                {history.length === 0 && <p className="text-xs text-gray-400">暂无执行动作</p>}
                {history.slice().reverse().map((item, idx) => (
                  <div key={`${item.timestamp}-${idx}`} className="text-[11px] bg-gray-50 border border-gray-200 rounded px-2 py-1">
                    <div className="font-medium text-gray-800">#{item.step} {item.action} {item.arm ? `(${item.arm})` : ''}</div>
                    {item.target && <div className="font-mono text-gray-600">T: {item.target.map((v) => v.toFixed(3)).join(', ')}</div>}
                    {item.actual && <div className="font-mono text-gray-600">A: {item.actual.map((v) => v.toFixed(3)).join(', ')}</div>}
                    <div className={item.success ? 'text-green-700' : 'text-red-600'}>
                      {item.success ? 'success' : 'failed'}{item.error !== undefined ? ` · err=${item.error.toFixed(4)}m` : ''}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

const ModelTree = ({ model }: { model: URDFModel | null }) => {
  if (!model) {
    return <p className="text-xs text-gray-400">加载模型中...</p>
  }

  const rootLinks = model.links.filter(
    (link) => !model.joints.some((joint) => joint.child === link.name),
  )

  return (
    <div className="space-y-1">
      {rootLinks.map((link) => (
        <TreeNode key={link.name} link={link} model={model} depth={0} />
      ))}
    </div>
  )
}

const TreeNode = ({
  link,
  model,
  depth,
}: {
  link: LinkInfo
  model: URDFModel
  depth: number
}) => {
  const children = model.joints
    .filter((joint) => joint.parent === link.name)
    .map((joint) => model.links.find((candidate) => candidate.name === joint.child))
    .filter(Boolean) as LinkInfo[]

  return (
    <div>
      <div
        className="flex items-center gap-2 rounded px-2 py-1 text-xs text-gray-700 hover:bg-gray-100"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <span className="w-3 text-gray-400">{children.length > 0 ? '›' : ''}</span>
        <span className="font-medium truncate" title={link.name}>{link.name}</span>
      </div>
      {children.map((child) => (
        <TreeNode key={child.name} link={child} model={model} depth={depth + 1} />
      ))}
    </div>
  )
}
