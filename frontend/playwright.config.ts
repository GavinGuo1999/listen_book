import { defineConfig } from "@playwright/test";

const e2eBackendUrl = "http://127.0.0.1:8001";
const e2eFrontendUrl = "http://127.0.0.1:5174";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  retries: 1,
  use: {
    baseURL: e2eFrontendUrl,
    headless: true,
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "npm run e2e:setup && npm run e2e:backend",
      url: `${e2eBackendUrl}/api/health`,
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5174",
      env: {
        VITE_API_PROXY_TARGET: e2eBackendUrl,
      },
      url: e2eFrontendUrl,
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
});
