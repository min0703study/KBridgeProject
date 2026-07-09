import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    // K-Bridge 워크스페이스 동시 기동 포트 배정(KBRIDGE_FRONTEND_PLAN.md §1-5):
    // admin 5173 / 학생앱(이 앱) 5174 / 시나리오 5175 / Mobile 5176
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://192.168.0.9:8050',
        changeOrigin: true,
      },
    },
  },
});
