export interface BackendDescriptor {
  backend_id: string
  display_name: string
  kind: string
  available: boolean
  capabilities: string[]
  extensions: Record<string, unknown>
}

export interface BackendsResponse {
  selected_backend: string
  backends: BackendDescriptor[]
}

export interface SceneRobotView {
  robot_id: string
  status: string
}

export interface SceneSnapshot {
  backend: string
  timestamp: number
  robots: SceneRobotView[]
  objects: Array<Record<string, unknown>>
  overlays: Array<Record<string, unknown>>
  metadata: Record<string, unknown>
}

export async function listBackends(): Promise<BackendsResponse> {
  const response = await fetch('/api/backends')
  if (!response.ok) {
    throw new Error(`Failed to load backends: ${response.status}`)
  }
  return response.json()
}

export async function selectBackend(backendId: string): Promise<{ selected_backend: string }> {
  const response = await fetch('/api/backends/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ backend_id: backendId }),
  })
  if (!response.ok) {
    throw new Error(`Failed to select backend: ${response.status}`)
  }
  return response.json()
}

export async function getSceneView(): Promise<SceneSnapshot> {
  const response = await fetch('/api/view/scene')
  if (!response.ok) {
    throw new Error(`Failed to load scene: ${response.status}`)
  }
  return response.json()
}
