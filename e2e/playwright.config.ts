import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests for the whole site (Django backend + TypeScript frontend).
 *
 * `npm test` starts the project with `python run.py` (or reuses it if it is
 * already running) and runs every file in ./tests in Chromium.
 * Set PYTHON if your Python command is not `python` (Windows) / `python3`.
 */
const python = process.env.PYTHON ?? (process.platform === "win32" ? "python" : "python3");

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  // one SQLite database behind the dev server → run the files one after another
  workers: 1,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:5173",
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } } }],
  webServer: {
    command: `${python} run.py --no-browser`,
    cwd: "..",
    // through the Vite proxy → ready only when frontend AND backend answer
    url: "http://localhost:5173/api/auth/me/",
    reuseExistingServer: true,
    timeout: 300_000, // the first run installs packages
    stdout: "ignore",
    stderr: "ignore", // the dev servers log every request; start `python run.py` yourself to see them
  },
});
