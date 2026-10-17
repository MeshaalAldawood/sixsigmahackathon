import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The page is served by the FastAPI app from app/static/, at whatever URL the app lives
// (http://localhost:8000/ or a Posit Connect content path like /content/<guid>/).
// base './' makes every asset path relative, and the API is fetched with relative
// 'api/...' URLs (src/api.js), so both work under any prefix.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
  server: {
    // `npm run dev` on :5173 forwards API calls to a backend started with testme.sh.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
