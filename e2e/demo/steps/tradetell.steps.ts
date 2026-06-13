import { createBdd } from "playwright-bdd";
import { expect, type Page } from "@playwright/test";

const { Given, When, Then } = createBdd();

// The first page load triggers initialize_rag_system() (knowledge-base load +
// embedding warm-up), which can take 1–3 minutes; and each answer round-trips
// through Groq. Give those beats room without flaking.
const RAG_INIT_TIMEOUT = 360_000;
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
  // The chat input only renders once RAG init has finished — wait on it so the
  // rest of the scenario doesn't race the warm-up spinner.
  await page
    .locator('[data-testid="stChatInput"] textarea')
    .waitFor({ state: "visible", timeout: RAG_INIT_TIMEOUT });
  await dwell(page);
});

Then("I see the {string} title", async ({ page }, title: string) => {
  await expect(page.locator(".app-title", { hasText: title })).toBeVisible();
  await dwell(page);
});

Then("I see example prompts in the sidebar", async ({ page }) => {
  const sidebar = page.locator('section[data-testid="stSidebar"]');
  await expect(sidebar.getByText("Try asking")).toBeVisible();
  // At least the first canned prompt chip is offered.
  await expect(
    sidebar.getByRole("button", {
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
  // A grounded answer ships a collapsed "📚 N source document(s)" expander.
  await expect(assistant.locator('[data-testid="stExpander"]')).toBeVisible();
  await dwell(page, 2500); // money shot — let the answer linger
});

When("I open the retrieved sources", async ({ page }) => {
  const assistant = page.locator('[data-testid="stChatMessage"]').nth(1);
  await assistant
    .locator('[data-testid="stExpander"]')
    .getByText(/source document\(s\)/)
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
