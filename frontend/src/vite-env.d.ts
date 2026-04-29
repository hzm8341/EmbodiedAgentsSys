/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_VUER_CLIENT_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
