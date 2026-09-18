import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev proxy -> FastAPI backend at :8000
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})