import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const API_TARGET = 'http://127.0.0.1:8000'
const proxied = ['/api', '/docs', '/openapi.json']

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const allowedHosts = (env.VITE_ALLOWED_HOSTS || '')
    .split(',')
    .map((host) => host.trim())
    .filter(Boolean)

  return {
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      allowedHosts: ['localhost', '127.0.0.1', ...allowedHosts],
      proxy: Object.fromEntries(
        proxied.map((p) => [p, { target: API_TARGET, changeOrigin: true }])
      ),
    },
    build: { outDir: 'dist', emptyOutDir: true },
  }
})
