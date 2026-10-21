import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api 요청은 Flask 서버(5000번)로 넘긴다.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:5000' },
  },
})
