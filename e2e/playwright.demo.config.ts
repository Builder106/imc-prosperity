import { defineConfig, devices } from "@playwright/test";
import { defineBddConfig } from "playwright-bdd";

// Demo recording config — single worker, video always on, slowMo pacing.
// QA config (when it exists) inverts all of this: parallel, no video, no slowMo.

const testDir = defineBddConfig({
  features: "demo/features/**/*.feature",
  steps: "demo/steps/**/*.ts",
  outputDir: ".features-gen/demo",
});

const SLOWMO = Number(process.env.DEMO_SLOWMO ?? 1200);
const VIEWPORT = { width: 2560, height: 1600 };

export default defineConfig({
  testDir,
  // Generous: the app's first use triggers initialize_rag_system() which can
  // take 1–3 minutes (knowledge-base load + embedding warm-up).
  timeout: 420_000,
  // Single worker + serial order: parallel workers compete for the video
  // subsystem and produce 0-byte webms (known Playwright quirk).
  fullyParallel: false,
  workers: 1,
  retries: 0, // a retry would record over the previous video
  reporter: [["list"]],
  expect: { timeout: 30_000 },
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:8501",
    headless: true, // headless still records video
    viewport: VIEWPORT,
    video: { mode: "on", size: VIEWPORT }, // size must match viewport exactly
    launchOptions: { slowMo: SLOWMO },
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Re-pin viewport + video at project level — the device preset
        // silently overrides the top-level `use` block.
        viewport: VIEWPORT,
        video: { mode: "on", size: VIEWPORT },
      },
    },
  ],
});
