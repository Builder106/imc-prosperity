import { createBdd } from "playwright-bdd";
import { expect, type Page } from "@playwright/test";

const { Given, When, Then } = createBdd();

// Research loads on demand, and each answer round-trips through Groq.
// Give that request room without slowing the market and replay views.
const RESEARCH_VIEW_TIMEOUT = 30_000;
const ANSWER_TIMEOUT = 360_000;

// Explicit dwell so "thing just appeared" beats read at 1x in the recording —
// slowMo only pauses between Playwright actions, not after goto()/assertions.
async function dwell(page: Page, ms = Number(process.env.DEMO_DWELL_MS ?? 1500)) {
  if (process.env.DEMO === "0") return;
  try {
    await page.waitForTimeout(ms);
  } catch {
    /* page already closed at end of scenario */
  }
}

Given("I open the trading assistant", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.getByText("Explore the market archive").waitFor({ state: "visible" });
  await dwell(page);
});

Then("I see the {string} title", async ({ page }, title: string) => {
  await expect(page.locator(".app-title", { hasText: title })).toBeVisible();
  await dwell(page);
});

When("I open Ask TradeTell", async ({ page }) => {
  await page.getByText("Ask TradeTell", { exact: true }).click();
  await page
    .locator('[data-testid="stChatInput"] textarea')
    .waitFor({ state: "visible", timeout: RESEARCH_VIEW_TIMEOUT });
});

Then("I see example prompts on the research desk", async ({ page }) => {
  await expect(page.getByText("Start with a question")).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: "What products and position limits are introduced in Round 1?",
    }),
  ).toBeVisible();
  await dwell(page);
});

When("I ask {string}", async ({ page }, question: string) => {
  const input = page.locator('[data-testid="stChatInput"] textarea').first();
  await input.click();
  await input.fill(question);
  await input.press("Enter");
  // Both bubbles mount immediately; the assistant bubble then holds the
  // "Retrieving context…" spinner until the answer streams in.
  await page
    .locator('[data-testid="stChatMessage"]')
    .nth(1)
    .waitFor({ state: "visible", timeout: ANSWER_TIMEOUT });
});

Then("the assistant answers with sources", async ({ page }) => {
  // The answer is rendered once the spinner status text detaches.
  await page
    .getByText("Retrieving context and generating an answer")
    .first()
    .waitFor({ state: "detached", timeout: ANSWER_TIMEOUT })
    .catch(() => {
      /* already resolved before we looked */
    });

  const assistant = page.locator('[data-testid="stChatMessage"]').nth(1);
  await expect(assistant).toBeVisible();
  // A grounded answer ships a collapsed source expander.
  await expect(assistant.locator('[data-testid="stExpander"]')).toBeVisible();
  await dwell(page, 2500); // money shot — let the answer linger
});

When("I open the retrieved sources", async ({ page }) => {
  const assistant = page.locator('[data-testid="stChatMessage"]').nth(1);
  await assistant
    .locator('[data-testid="stExpander"]')
    .getByText(/Sources \(\d+\)/)
    .click();
  await dwell(page);
});

Then("I see the retrieved source documents", async ({ page }) => {
  const assistant = page.locator('[data-testid="stChatMessage"]').nth(1);
  const expander = assistant.locator('[data-testid="stExpander"]');
  // Once expanded, each source renders a fenced code block of its content.
  await expect(expander.locator("code").first()).toBeVisible();
  await dwell(page, 2500);
});
