import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@/components': resolve(__dirname, 'src/components'),
      '@/pages': resolve(__dirname, 'src/pages'),
      '@/services': resolve(__dirname, 'src/services'),
      '@/stores': resolve(__dirname, 'src/stores'),
      '@/styles': resolve(__dirname, 'src/styles'),
      '@/utils': resolve(__dirname, 'src/utils'),
      '@/types': resolve(__dirname, 'src/types'),
    },
  },
  server: {
    // Use SF_FRONTEND_PORT if provided to avoid clashing with other apps
    port: parseInt(process.env.SF_FRONTEND_PORT || '5175', 10),
    proxy: {
      '/api': {
        // Allow overriding backend port via env variable (default 5001)
        target: `http://localhost:${process.env.SF_API_PORT || '5001'}`,
        changeOrigin: true,
      },
      '/socket.io': {
        // Proxy Socket.IO requests to backend
        target: `http://localhost:${process.env.SF_API_PORT || '5001'}`,
        changeOrigin: true,
        ws: true, // Enable WebSocket proxying
      },
    },
  },
  build: {
    // Flask serves the SPA from ../../mission-control-dist
    // Emit the production bundle straight there so the backend always
    // picks up the latest build without a manual copy step.
    outDir: resolve(__dirname, '..', 'mission-control-dist'),
    emptyOutDir: true,
    sourcemap: true,
  },
})