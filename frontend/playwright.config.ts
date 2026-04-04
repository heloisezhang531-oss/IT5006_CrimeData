import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 180_000,
  use: {
    baseURL: 'http://localhost:3100',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  reporter: 'line',
  webServer: [
    {
      command: '.\\.venv\\Scripts\\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8002',
      url: 'http://127.0.0.1:8002/api/health',
      reuseExistingServer: false,
      timeout: 120_000,
      cwd: '..',
    },
    {
      command: 'npm run dev -- --port 3100',
      url: 'http://localhost:3100',
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_API_BASE: 'http://127.0.0.1:8002/api',
        INTERNAL_API_BASE: 'http://127.0.0.1:8002/api',
      },
    },
  ],
});
